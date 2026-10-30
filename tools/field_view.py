"""Derive a private USD view from one upstream cached reference and candidate mesh.

The source cache does not identify its generation geometry. This adapter does not
establish a matched result or run inference. Coordinate GPU use before execution.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade, Vt
import warp as wp


PRIVATE = Path(__file__).resolve().parents[1] / "build/private"


@wp.kernel
def _speed_colors(speed: wp.array(dtype=wp.float32), limit: float,
                  colors: wp.array(dtype=wp.vec3f)):
    i = wp.tid()
    u = wp.clamp(speed[i] / limit, 0.0, 1.0)
    low, middle, high = wp.vec3f(.02, .18, .45), wp.vec3f(.05, .78, .9), wp.vec3f(1, .3, .05)
    if u < .5:
        colors[i] = wp.lerp(low, middle, u * 2.0)
    else:
        colors[i] = wp.lerp(middle, high, (u - .5) * 2.0)


def _ply(path):
    """Read only the approved binary XYZ/triangle/STL-tag layout."""
    with path.open("rb") as stream:
        header = []
        while True:
            line = stream.readline()
            if not line or len(header) >= 32:
                raise ValueError("Incomplete PLY header")
            text = line.decode("ascii").strip()
            header.append(text)
            if text == "end_header":
                break
        layout = [line for line in header if not line.startswith("comment ")]
        vertex_count = int(layout[2].removeprefix("element vertex "))
        face_count = int(layout[6].removeprefix("element face "))
        expected = ["ply", "format binary_little_endian 1.0", f"element vertex {vertex_count}",
                    "property float x", "property float y", "property float z",
                    f"element face {face_count}", "property list uchar int vertex_indices",
                    "property ushort stl", "end_header"]
        if layout != expected:
            raise ValueError("Unsupported PLY layout; expected the approved XYZ triangle mesh")
        points = np.fromfile(stream, dtype="<f4", count=vertex_count * 3).reshape(-1, 3)
        faces = np.fromfile(stream, dtype=np.dtype([
            ("count", "u1"), ("indices", "<i4", (3,)), ("stl", "<u2")]), count=face_count)
        if (len(points) != vertex_count or len(faces) != face_count or stream.read(1)
                or not (faces["count"] == 3).all() or not np.isfinite(points).all()
                or faces["indices"].min() < 0 or faces["indices"].max() >= vertex_count):
            raise ValueError("Invalid PLY triangle data")
    return points, np.ascontiguousarray(faces["indices"].reshape(-1))


def _mesh(stage, path, points, counts, indices):
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(points, dtype=np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.ascontiguousarray(counts, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.ascontiguousarray(indices, dtype=np.int32)))
    mesh.CreateSubdivisionSchemeAttr("none")
    return mesh


def _material(stage, name, color):
    material = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
    shader = UsdShade.Shader.Define(stage, f"{material.GetPath()}/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    diffuse = shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(.45)
    if color is None:
        reader = UsdShade.Shader.Define(stage, f"{material.GetPath()}/Color")
        reader.CreateIdAttr("UsdPrimvarReader_float3")
        reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
        reader.CreateOutput("result", Sdf.ValueTypeNames.Float3)
        diffuse.ConnectToSource(reader.ConnectableAPI(), "result")
    else:
        diffuse.Set(Gf.Vec3f(*color))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def build(cache: Path, mesh: Path, destination: Path):
    """Write a fresh private reference.usdc and provenance.json; return its record."""
    cache, mesh, destination = Path(cache).resolve(strict=True), Path(mesh).resolve(strict=True), Path(destination).resolve()
    if not destination.is_relative_to(PRIVATE.resolve()) or destination == PRIVATE.resolve():
        raise ValueError("Field views must stay in a child directory of build/private")
    if destination.exists():
        raise FileExistsError(destination)
    from warp_simdata import AssociationType, Field
    from warp_simdata.data_models.custom import point_cloud
    from warp_simdata.data_models.vtk import image_data
    from warp_simdata.operators import slice as plane_slice, streamlines

    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (cache, mesh)}
    case = json.loads(cache.with_suffix(".json").read_text(encoding="utf-8"))
    velocity = float(case["app_state"]["omni:rtwt:app_state:velocity"])
    if velocity <= 0:
        raise ValueError("The cached reference must state a positive free-stream speed")
    points, indices = _ply(mesh)
    wp.config.quiet = True
    with np.load(cache, allow_pickle=False) as arrays:
        lower, upper = arrays["EXTENT_MIN"].astype(np.int32), arrays["EXTENT_MAX"].astype(np.int32)
        dimensions = upper - lower + 1
        fields, transforms = {}, {}
        for wire, name in (("nvdb_velocity", "Velocity"), ("nvdb_velocity_magnitude", "Speed")):
            volume = wp.Volume(wp.array(np.ascontiguousarray(arrays[wire]), dtype=wp.uint8, device="cuda:0"))
            info = volume.get_grid_info()
            matrix = np.array(info.transform_matrix, dtype=np.float32).reshape(3, 3)
            origin = np.array(info.translation, dtype=np.float32)
            spacing = np.diag(matrix).copy()
            if not np.allclose(matrix, np.diag(spacing), rtol=0, atol=1e-8) or (spacing <= 0).any():
                raise ValueError("This cached-reference adapter requires an axis-aligned positive grid")
            transforms[name] = {"translation": origin.tolist(), "linear": matrix.tolist()}
            fields[name] = Field.from_volume(volume, wp.vec3i(*dimensions), AssociationType.NODE,
                                            origin=wp.vec3i(*lower))
        if transforms["Velocity"] != transforms["Speed"]:
            raise ValueError("Velocity and speed use different coordinate frames")
    dataset = image_data.create_dataset(wp.vec3f(*origin), wp.vec3f(*spacing),
                                        wp.vec3i(*lower), wp.vec3i(*upper), device="cuda:0")
    for name, field in fields.items():
        dataset.add_field(name, field)
    mesh_center = (points.min(axis=0) + points.max(axis=0)) / 2
    surface = plane_slice.compute(dataset, origin=tuple(mesh_center), normal=(0, 0, 1), field_names=["Speed"])
    colors = wp.empty(surface.get_num_nodes(), dtype=wp.vec3f, device="cuda:0")
    wp.launch(_speed_colors, surface.get_num_nodes(), inputs=[surface.get_field("Speed").to_array(),
              velocity * 1.5, colors], device="cuda:0")
    domain_min, domain_max = origin + spacing * lower, origin + spacing * upper
    seeds = [(float(domain_min[0] + 2 * spacing[0]),
              float(domain_min[1] + fy * (domain_max[1] - domain_min[1])),
              float(domain_min[2] + fz * (domain_max[2] - domain_min[2])))
             for fy in (.1, .2, .3, .4, .5, .6, .7, .8, .9) for fz in (.2, .4, .6, .8)]
    trajectories = streamlines.compute(dataset, "Velocity", point_cloud.create_dataset(
        wp.array(seeds, dtype=wp.vec3f, device="cuda:0")), initial_dt=.005, min_dt=.0002,
        max_dt=.02, max_steps=160, tolerance=1e-4, direction=streamlines.Direction.FORWARD)

    stage = Usd.Stage.CreateInMemory()
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    UsdGeom.SetStageUpAxis(stage, "Z")
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    stage.SetTimeCodesPerSecond(30)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(0)
    UsdGeom.Scope.Define(stage, "/World/Looks")
    car = _mesh(stage, "/World/CandidateMesh", points, np.full(len(indices) // 3, 3, dtype=np.int32), indices)
    UsdShade.MaterialBindingAPI.Apply(car.GetPrim()).Bind(_material(stage, "Candidate", (.18, .22, .27)))
    cut = _mesh(stage, "/World/SpeedSlice", surface.handle.points.numpy(),
                surface.handle.face_vertex_counts.numpy(), surface.handle.face_vertex_indices.numpy())
    cut.CreateDoubleSidedAttr(True)
    UsdGeom.PrimvarsAPI(cut).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray,
        UsdGeom.Tokens.vertex).Set(Vt.Vec3fArray.FromNumpy(colors.numpy()))
    UsdShade.MaterialBindingAPI.Apply(cut.GetPrim()).Bind(_material(stage, "Speed", None))
    curve_count = 0
    if trajectories is not None:
        curves = UsdGeom.BasisCurves.Define(stage, "/World/Streamlines")
        curves.CreateTypeAttr("linear")
        curves.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(trajectories.handle.points.numpy()))
        counts = trajectories.handle.curve_vertex_counts.numpy()
        curves.CreateCurveVertexCountsAttr(Vt.IntArray.FromNumpy(counts))
        curves.CreateWidthsAttr([.012])
        curves.SetWidthsInterpolation("constant")
        UsdShade.MaterialBindingAPI.Apply(curves.GetPrim()).Bind(_material(stage, "Lines", (.95, .45, .08)))
        curve_count = len(counts)
    dome = UsdLux.DomeLight.Define(stage, "/World/Sky")
    dome.CreateIntensityAttr(500)
    key = UsdLux.RectLight.Define(stage, "/World/Key")
    key.CreateWidthAttr(8)
    key.CreateHeightAttr(6)
    key.CreateIntensityAttr(4000)
    key.AddTranslateOp().Set(Gf.Vec3d(3, -3, 8))
    center = Gf.Vec3d(*map(float, (domain_min + domain_max) / 2))
    radius = float(np.linalg.norm(domain_max - domain_min) / 2)
    eye = center + Gf.Vec3d(1, -1, .7).GetNormalized() * radius * 2.5
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera.CreateFocalLengthAttr(35)
    camera.CreateHorizontalApertureAttr(36)
    camera.CreateVerticalApertureAttr(20.25)
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye, center, Gf.Vec3d(0, 0, 1)).GetInverse())
    product = UsdRender.Product.Define(stage, "/Render/Field")
    product.CreateCameraRel().SetTargets([camera.GetPath()])
    product.CreateResolutionAttr(Gf.Vec2i(960, 540))
    color = UsdRender.Var.Define(stage, "/Render/Field/Color")
    color.CreateSourceNameAttr("LdrColor")
    product.CreateOrderedVarsRel().SetTargets([color.GetPath()])
    product.GetPrim().CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token).Set("PathTracing")
    record = {"status": "cached_reference_unverified", "private": True,
              "sources": hashes, "case": case, "grid": {"min": lower.tolist(), "max": upper.tolist(),
              "transforms": transforms}, "speed_color_range_m_s": [0, velocity * 1.5],
              "slice_origin_m": mesh_center.tolist(), "streamlines": curve_count,
              "provenance_gap": "The cache does not identify its generation geometry or ride height. The candidate mesh match is not verified.",
              "visualization": "A slice and steady-field streamlines from an upstream cache. No inference or transient solve was run."}
    stage.GetRootLayer().customLayerData = {"stagewright:resultStatus": record["status"],
        "stagewright:cacheSha256": hashes[str(cache)], "stagewright:meshSha256": hashes[str(mesh)],
        "stagewright:provenanceGap": record["provenance_gap"]}
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
        raise RuntimeError("A source changed during field processing")
    destination.mkdir(parents=True, exist_ok=False)
    if not stage.GetRootLayer().Export(str(destination / "reference.usdc")):
        raise RuntimeError("Could not export the private reference stage")
    record["scene"] = str(destination / "reference.usdc")
    (destination / "provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.cache, args.mesh, args.destination), indent=2))
