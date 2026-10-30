"""Prepare an app-owned streaming render product without changing the source stage."""
import math
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdRender, UsdShade


def prepare(source: Path, destination: Path, width=960, height=540, spp=16):
    """Write a new USDA wrapper and return its streaming product and replay bounds."""
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    if destination.suffix.lower() != ".usda":
        raise ValueError("The viewer wrapper must use a .usda destination")
    if min(width, height, spp) < 1:
        raise ValueError("Resolution and sample count must be positive")
    original = Usd.Stage.Open(str(source))
    if not original:
        raise ValueError(f"Cannot open USD stage: {source}")
    if original.GetPrimAtPath("/StagewrightView"):
        raise ValueError("The source already uses the app-owned /StagewrightView namespace")

    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths = [source.as_posix()]
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(original))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(original))
    UsdPhysics.SetStageKilogramsPerUnit(stage, UsdPhysics.GetStageKilogramsPerUnit(original))
    rate = original.GetTimeCodesPerSecond()
    stage.SetTimeCodesPerSecond(rate)
    stage.SetFramesPerSecond(original.GetFramesPerSecond())
    stage.SetStartTimeCode(original.GetStartTimeCode())
    stage.SetEndTimeCode(original.GetEndTimeCode())
    if original.GetDefaultPrim():
        stage.SetDefaultPrim(stage.GetPrimAtPath(original.GetDefaultPrim().GetPath()))
    UsdGeom.Scope.Define(stage, "/StagewrightView")

    camera_path = next((prim.GetPath() for prim in original.Traverse()
                        if prim.IsA(UsdGeom.Camera)), None)
    if camera_path is None:
        bounds = UsdGeom.BBoxCache(Usd.TimeCode(original.GetStartTimeCode()),
                                  [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                                  useExtentsHint=True).ComputeWorldBound(original.GetPseudoRoot())
        bounds = bounds.ComputeAlignedRange()
        center = Gf.Vec3d(0) if bounds.IsEmpty() else bounds.GetMidpoint()
        radius = 1.0 if bounds.IsEmpty() else max(bounds.GetSize().GetLength() / 2, 1e-4)
        aspect = width / height
        aperture, focal = 36.0, 35.0
        half_angle = math.atan(min(aperture, aperture / aspect) / (2 * focal))
        distance = radius / math.sin(half_angle) * 1.1
        if UsdGeom.GetStageUpAxis(original) == UsdGeom.Tokens.z:
            up, direction = Gf.Vec3d(0, 0, 1), Gf.Vec3d(1, -1, .65)
        else:
            up, direction = Gf.Vec3d(0, 1, 0), Gf.Vec3d(1, .65, 1)
        eye = center + direction.GetNormalized() * distance
        camera = UsdGeom.Camera.Define(stage, "/StagewrightView/Camera")
        camera.CreateFocalLengthAttr(focal)
        camera.CreateHorizontalApertureAttr(aperture)
        camera.CreateVerticalApertureAttr(aperture / aspect)
        camera.CreateClippingRangeAttr(Gf.Vec2f(radius * .001, distance + radius * 2))
        camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye, center, up).GetInverse())
        camera_path = camera.GetPath()

    product = UsdRender.Product.Define(stage, "/StagewrightView/Render")
    product.CreateResolutionAttr(Gf.Vec2i(width, height))
    product.CreateCameraRel().SetTargets([camera_path])
    prim = product.GetPrim()
    prim.CreateAttribute("deviceIds", Sdf.ValueTypeNames.UIntArray).Set([0])
    prim.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token).Set("PathTracing")
    prim.CreateAttribute("omni:rtx:pt:samplesPerPixel", Sdf.ValueTypeNames.UInt).Set(spp)
    prim.CreateAttribute("omni:rtx:pt:samplesPerIteration", Sdf.ValueTypeNames.Int).Set(math.gcd(spp, 4))

    color = UsdRender.Var.Define(stage, f"{product.GetPath()}/Color")
    color.CreateSourceNameAttr("LdrColor")
    color_aov = color.GetPrim().CreateAttribute("omni:rtx:aov", Sdf.ValueTypeNames.Opaque)
    bgra = UsdRender.Var.Define(stage, f"{product.GetPath()}/BGRA")
    bgra.CreateSourceNameAttr("BgraColor")
    shader = UsdShade.Shader.Define(stage, f"{product.GetPath()}/Swizzle")
    shader.CreateIdAttr("spg:rtx.spg.stdlib/Swizzle")
    shader.CreateInput("swizzle", Sdf.ValueTypeNames.Token).Set("zyxw")
    shader.CreateInput("Input", Sdf.ValueTypeNames.Opaque).GetAttr().SetConnections([color_aov.GetPath()])
    output = shader.CreateOutput("Output", Sdf.ValueTypeNames.Opaque)
    bgra.GetPrim().CreateAttribute("omni:rtx:aov", Sdf.ValueTypeNames.Opaque).SetConnections(
        [output.GetAttr().GetPath()])
    product.CreateOrderedVarsRel().SetTargets([color.GetPath(), bgra.GetPath()])

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(stage.GetRootLayer().ExportToString())
    return {"product": str(product.GetPath()), "var": str(bgra.GetPath()),
            "width": width, "height": height,
            "start": original.GetStartTimeCode() / rate,
            "end": original.GetEndTimeCode() / rate,
            "source": str(source), "camera": str(camera_path)}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--spp", type=int, default=16)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination, args.width, args.height, args.spp)))
