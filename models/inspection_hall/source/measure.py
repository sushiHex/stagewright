"""Assess frozen USD geometry against actual solver poses; no native physics or renderer."""
import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

DECK = "/World/Mechanism/FrontLeafDeck"
ROOF = "/World/Mechanism/RoofInput"


def rotations(q):
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    x, y, z, w = np.moveaxis(q, -1, 0)
    return np.stack((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w),
                     2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w),
                     2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)), axis=-1).reshape(q.shape[:-1]+(3, 3))


def corners(lo, hi):
    return np.array(list(itertools.product(*zip(lo, hi))), dtype=float)


def rectangle_area(lo, hi, region_lo, region_hi):
    """Exact union of clipped axis-aligned rectangles, no pixel approximation."""
    lo, hi = np.maximum(lo, region_lo), np.minimum(hi, region_hi)
    valid = np.all(hi-lo > 1e-8, axis=1)
    lo, hi = lo[valid], hi[valid]
    if not len(lo):
        return 0.0
    # A bounding rectangle already covering the whole region makes the union trivial.
    if np.any(np.all(lo <= np.asarray(region_lo)+1e-9, axis=1) & np.all(hi >= np.asarray(region_hi)-1e-9, axis=1)):
        return float(np.prod(np.asarray(region_hi)-region_lo))
    xs, ys = np.unique(np.r_[lo[:, 0], hi[:, 0]]), np.unique(np.r_[lo[:, 1], hi[:, 1]])
    x0, x1 = np.searchsorted(xs, lo[:, 0]), np.searchsorted(xs, hi[:, 0])
    y0, y1 = np.searchsorted(ys, lo[:, 1]), np.searchsorted(ys, hi[:, 1])
    grid = np.zeros((len(xs), len(ys)), dtype=np.int32)
    np.add.at(grid, (x0, y0), 1)
    np.add.at(grid, (x1, y0), -1)
    np.add.at(grid, (x0, y1), -1)
    np.add.at(grid, (x1, y1), 1)
    cover = grid.cumsum(0).cumsum(1)[:-1, :-1] > 0
    return float(np.sum(cover * np.diff(xs)[:, None] * np.diff(ys)[None, :]))


def clearance(lo, hi, a, b, slab_axis, slab, axes, exclude=None):
    mask = (hi[:, slab_axis] > slab[0]+1e-7) & (lo[:, slab_axis] < slab[1]-1e-7)
    if exclude is not None:
        mask &= ~exclude
    area = rectangle_area(lo[mask][:, axes], hi[mask][:, axes], a, b)
    return max(0., 1.-area/np.prod(np.asarray(b)-a))


def geometry(stage, paths):
    cache = UsdGeom.XformCache()
    data, names, members = [], [], []
    inverse = {p: cache.GetLocalToWorldTransform(stage.GetPrimAtPath(p)).GetInverse() for p in paths}
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Boundable):
            continue
        if UsdGeom.Imageable(prim).ComputeVisibility() == "invisible":
            continue
        g = UsdGeom.Boundable(prim)
        extent = g.GetExtentAttr().Get()
        if extent is None or len(extent) != 2:
            extent = UsdGeom.Boundable.ComputeExtentFromPlugins(g, Usd.TimeCode.Default())
        if extent is None or len(extent) != 2:
            raise RuntimeError(f"No geometric extent: {prim.GetPath()}")
        name = str(prim.GetPath())
        member = next((i for i, p in enumerate(paths) if name.startswith(p+"/")), -1)
        m = cache.GetLocalToWorldTransform(prim)
        if member >= 0:
            m = m * inverse[paths[member]]
        data.append(np.array([m.Transform(Gf.Vec3d(*p)) for p in corners(extent[0], extent[1])]))
        names.append(name)
        members.append(member)
    return np.array(data), np.array(names), np.array(members)


def joint_errors(stage, paths, positions, rots):
    errors, axis_errors = {}, {}
    n = len(positions)
    for p in stage.Traverse():
        if not p.IsA(UsdPhysics.Joint):
            continue
        j = UsdPhysics.Joint(p)
        world, axes = [], []
        for side in (0, 1):
            rel = getattr(j, f"GetBody{side}Rel")().GetTargets()
            local = np.array(getattr(j, f"GetLocalPos{side}Attr")().Get(), dtype=float)
            quat = getattr(j, f"GetLocalRot{side}Attr")().Get()
            axis = np.array(Gf.Rotation(quat).TransformDir(Gf.Vec3d(1, 0, 0)))
            if not rel:
                world.append(np.broadcast_to(local, (n, 3)))
                axes.append(np.broadcast_to(axis, (n, 3)))
            else:
                idx = paths.index(str(rel[0]))
                world.append(np.einsum("tij,j->ti", rots[:, idx], local)+positions[:, idx])
                axes.append(np.einsum("tij,j->ti", rots[:, idx], axis))
        errors[str(p.GetPath())] = np.linalg.norm(world[1]-world[0], axis=1)
        dot = np.clip((axes[0]*axes[1]).sum(axis=1), -1, 1)
        axis_errors[str(p.GetPath())] = np.degrees(np.arccos(dot))
    return errors, axis_errors


def compare_candidates(powered, control):
    a, b = Usd.Stage.Open(str(powered)), Usd.Stage.Open(str(control))
    def values(stage):
        result = {}
        for p in stage.Traverse():
            result[str(p.GetPath())+"@type"] = p.GetTypeName()
            result[str(p.GetPath())+"@schemas"] = repr(p.GetAppliedSchemas())
            for prop in p.GetProperties():
                key = str(prop.GetPath())
                result[key] = repr(prop.Get()) if isinstance(prop, Usd.Attribute) else repr(prop.GetTargets())
        return result
    va, vb = values(a), values(b)
    differences = {p: {"powered": va.get(p), "control": vb.get(p)}
                   for p in va.keys() | vb.keys() if va.get(p) != vb.get(p)}
    expected = {"/World/Joints/M01_Roof.drive:angular:physics:"+s for s in ("stiffness", "damping", "maxForce")}
    return {"only_three_disabled_drive_settings": set(differences) == expected, "differences": differences}


def assess(result, out, design, control=False):
    out.mkdir(parents=True, exist_ok=False)
    p = json.loads(design.read_text())
    c = p["useful_operation"]
    stage = Usd.Stage.Open(str(result / "input.usdz"))
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    record = json.loads((result / "recording/result.json").read_text())
    digest = hashlib.sha256((result / "input.usdz").read_bytes()).hexdigest()
    assert digest == record["source_sha256"]
    with np.load(result / "recording/poses.npz", allow_pickle=False) as npz:
        paths = list(map(str, npz["paths"]))
        poses, seconds = npz["poses"].copy(), npz["seconds"].copy()
    assert poses.shape == (2400, 3, 7)
    assert record["quaternion_order"] == "xyzw"
    assert np.isfinite(poses).all()
    rots = rotations(poses[..., 3:])
    positions = poses[..., :3]
    di, ri = paths.index(DECK), paths.index(ROOF)
    data, names, members = geometry(stage, paths)
    floor = names == DECK+"/FloorSlab"
    patch = np.array([[x, p["deck_walking_face_local_y_m"], z]
                      for x in c["deck_local_x_m"] for z in c["deck_local_z_m"]])
    patch_world = np.einsum("tij,kj->tki", rots[:, di], patch)+positions[:, di, None]
    normal = np.einsum("tij,j->ti", rots[:, di], [0, -1, 0])
    tilt = np.degrees(np.arccos(np.clip(normal[:, 2], -1, 1)))
    hold = seconds >= c["hold_start_s"]-1e-9
    hold_start = np.flatnonzero(hold)[0]
    hold_travel = np.linalg.norm(patch_world-patch_world[hold_start], axis=-1).max(axis=1)
    errors, axis_errors = joint_errors(stage, paths, positions, rots)
    max_error = np.max(np.stack(list(errors.values())), axis=0)
    # Access endpoints are evaluated on the recorded moving face, at the hinge-side edge.
    access = np.array([[x, p["deck_walking_face_local_y_m"], 0] for x in c["access_x_m"]])
    access_world = np.einsum("tij,kj->tki", rots[:, di], access)+positions[:, di, None]
    gap = np.max(np.abs(access_world[:, :, 1]-c["landing_front_y_m"]), axis=1)
    step = np.max(np.abs(access_world[:, :, 2]-c["deck_height_m"]), axis=1)
    lateral = np.max(np.abs(access_world[:, :, 0]-access[:, 0]), axis=1)
    cam = UsdGeom.Camera(stage.GetPrimAtPath("/World/Cameras/InspectionWide")).GetCamera()
    fr = cam.frustum
    view_projection = np.array(fr.ComputeViewMatrix()*fr.ComputeProjectionMatrix())

    def spatial(pos, rotation):
        world = data.copy()
        for i in range(len(paths)):
            mask = members == i
            world[mask] = data[mask] @ rotation[i].T + pos[i]
        lo, hi = world.min(axis=1), world.max(axis=1)
        portal = clearance(lo, hi, [c["portal_x_m"][0], c["portal_z_m"][0]],
                           [c["portal_x_m"][1], c["portal_z_m"][1]], 1, c["portal_y_slab_m"], [0, 2])
        court = clearance(lo, hi, [c["court_x_m"][0], c["court_y_m"][0]],
                          [c["court_x_m"][1], c["court_y_m"][1]], 2, c["court_z_m"], [0, 1])
        deck_local = (world-pos[di]) @ rotation[di]
        dlo, dhi = deck_local.min(axis=1), deck_local.max(axis=1)
        slab = [p["deck_walking_face_local_y_m"]-c["deck_headroom_m"], p["deck_walking_face_local_y_m"]-.03]
        deck_clear = clearance(dlo, dhi, [c["deck_local_x_m"][0], c["deck_local_z_m"][0]],
                               [c["deck_local_x_m"][1], c["deck_local_z_m"][1]], 1, slab, [0, 2], floor)
        throat = clearance(dlo, dhi, [10.35, -.35], [12.05, .4], 1, slab, [0, 2], floor)
        moving = world[members >= 0].reshape(-1, 3)
        clip = np.c_[moving, np.ones(len(moving))] @ view_projection
        ndc = clip[:, :3] / clip[:, 3, None]
        camera_inside = bool(np.all(clip[:, 3] > 0) and np.all(np.abs(ndc) <= 1))
        return dict(portal_clear_fraction=portal, overhead_open_fraction=court,
                    deck_headroom_clear_fraction=deck_clear, access_clear_fraction=throat,
                    mechanism_inside_wide_frustum=camera_inside), world

    cache = UsdGeom.XformCache()
    init_p, init_r = [], []
    for path in paths:
        m = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(path))
        init_p.append(np.array(m.ExtractTranslation()))
        init_r.append(np.array(m.ExtractRotationMatrix()).T)
    initial, _ = spatial(np.array(init_p), np.array(init_r))
    rows = []
    # Full recorded trace: every sample, not an interpolation or ideal kinematic trajectory.
    for i, t in enumerate(seconds):
        row, _ = spatial(positions[i], rots[i])
        row.update(seconds=float(t), deck_tilt_deg=float(tilt[i]),
                   deck_patch_min_z_m=float(patch_world[i, :, 2].min()),
                   deck_patch_max_z_m=float(patch_world[i, :, 2].max()),
                   access_gap_m=float(gap[i]), access_step_m=float(step[i]),
                   access_lateral_drift_m=float(lateral[i]), max_joint_anchor_error_m=float(max_error[i]),
                   deck_corner_travel_from_hold_start_m=float(hold_travel[i]))
        rows.append(row)
    final = [r for r, keep in zip(rows, hold) if keep]
    def minimum(name): return float(min(r[name] for r in final))
    def maximum(name): return float(max(r[name] for r in final))
    checks = {
        "authored_portal_closed": initial["portal_clear_fraction"] <= .05,
        "authored_court_covered": initial["overhead_open_fraction"] <= .05,
        "portal_open": minimum("portal_clear_fraction") >= c["portal_min_clear_fraction"],
        "court_open": minimum("overhead_open_fraction") >= c["court_min_open_fraction"],
        "deck_level": maximum("deck_tilt_deg") <= c["deck_max_tilt_deg"],
        "deck_height": minimum("deck_patch_min_z_m") >= c["deck_height_m"]-c["deck_height_tolerance_m"]
                       and maximum("deck_patch_max_z_m") <= c["deck_height_m"]+c["deck_height_tolerance_m"],
        "deck_headroom": minimum("deck_headroom_clear_fraction") >= c["deck_min_clear_fraction"],
        "access_alignment": maximum("access_gap_m") <= c["access_max_gap_m"]
                            and maximum("access_step_m") <= c["access_max_step_m"] and maximum("access_lateral_drift_m") <= .05,
        "access_clear": minimum("access_clear_fraction") >= 1.-1e-6,
        "joint_integrity_all_samples": float(max_error.max()) <= c["max_joint_anchor_error_m"],
        "deck_stationary_hold": maximum("deck_corner_travel_from_hold_start_m") <= c["max_deck_hold_corner_travel_m"],
    }
    # Attribution at the final recorded sample, using conservative boxes.
    _, end_world = spatial(positions[-1], rots[-1])
    elo, ehi = end_world.min(1), end_world.max(1)
    obstruct = (ehi[:, 2] > c["court_z_m"][0]) & (elo[:, 2] < c["court_z_m"][1])
    obstructions = []
    for n, a, b in zip(names[obstruct], elo[obstruct], ehi[obstruct]):
        area = rectangle_area(a[None, :2], b[None, :2], [c["court_x_m"][0], c["court_y_m"][0]],
                              [c["court_x_m"][1], c["court_y_m"][1]])
        if area > .01:
            obstructions.append(dict(path=str(n), projected_area_m2=area, world_min=a.tolist(), world_max=b.tolist()))
    roof_angles = np.degrees(2*np.arccos(np.clip(np.abs(poses[:, ri, 6]), 0, 1)))
    deck_angles = np.degrees(2*np.arccos(np.clip(np.abs(poses[:, di, 6]), 0, 1)))
    prediction = None
    if control:
        prediction = {
            "roof_within_2_deg_all_samples": float(roof_angles.max()) <= 2,
            "deck_within_2_deg_all_samples": float(deck_angles.max()) <= 2,
            "portal_stays_closed": max(r["portal_clear_fraction"] for r in rows) <= .05,
            "court_stays_covered": max(r["overhead_open_fraction"] for r in rows) <= .05,
            "deck_does_not_deploy": not checks["deck_level"] and not checks["deck_height"],
        }
    report = {
        "result_directory": str(result), "frozen_input_sha256": digest,
        "poses_sha256": hashlib.sha256((result / "recording/poses.npz").read_bytes()).hexdigest(),
        "design_revision": p.get("revision"), "useful_operation": c,
        "samples": len(rows), "seconds": [float(seconds[0]), float(seconds[-1])],
        "hold_samples": len(final), "hold_seconds": [float(seconds[hold_start]), float(seconds[-1])],
        "pose_devices": record["pose_devices"], "packages": record["packages"],
        "geometry_count_including_instance_proxies": len(names),
        "authored_initial": initial, "first_solver_sample": rows[0], "last_solver_sample": rows[-1],
        "useful_operation_pass": all(checks.values()), "conditions": checks,
        "final_interval_minimum": {k: minimum(k) for k in final[0] if k != "seconds"},
        "final_interval_maximum": {k: maximum(k) for k in final[0] if k != "seconds"},
        "maximum_joint_anchor_error_m_all_samples": {k: float(v.max()) for k, v in errors.items()},
        "maximum_joint_axis_misalignment_deg_all_samples": {k: float(v.max()) for k, v in axis_errors.items()},
        "maximum_roof_rotation_deg": float(roof_angles.max()), "maximum_deck_rotation_deg": float(deck_angles.max()),
        "motor_disabled_prediction": prediction,
        "motor_disabled_prediction_pass": all(prediction.values()) if prediction is not None else None,
        "final_overhead_obstructions": sorted(obstructions, key=lambda d: -d["projected_area_m2"]),
        "wide_camera_contains_mechanism_all_samples": all(r["mechanism_inside_wide_frustum"] for r in rows),
        "limits": "Bounding-box geometry assessment and unloaded recorded rigid poses only. No forces, structural analysis, contact report, occupied test or rendering."
    }
    (out / "assessment.json").write_text(json.dumps(report, indent=2)+"\n")
    with (out / "per_sample.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Actual recorded poses presented as inspectable static USD stages, explicitly labelled.
    for index, slug in ((0, "first_recorded"), (1199, "ten_seconds"), (2399, "last_recorded")):
        snap = Usd.Stage.CreateNew(str(out / (slug+".usda")))
        import os
        snap.GetRootLayer().subLayerPaths = [os.path.relpath(result / "input.usdz", out).replace("\\", "/")]
        for key in ("defaultPrim", "upAxis", "metersPerUnit", "kilogramsPerUnit"):
            snap.SetMetadata(key, stage.GetMetadata(key))
        snap.GetRootLayer().documentation = f"Actual solver pose at {seconds[index]:.9f} s; static inspection snapshot, not an independent simulation."
        snap.GetRootLayer().customLayerData = {"preferredCamera": "/World/Cameras/InspectionWide", "recordedSeconds": float(seconds[index])}
        for path, pose in zip(paths, poses[index]):
            x, y, z, w = map(float, pose[3:])
            m = Gf.Matrix4d().SetRotate(Gf.Quatd(w, Gf.Vec3d(x, y, z)))
            m.SetTranslateOnly(Gf.Vec3d(*map(float, pose[:3])))
            xf = UsdGeom.Xformable(snap.GetPrimAtPath(path))
            op = xf.AddTransformOp(opSuffix="recordedSnapshot")
            xf.SetXformOpOrder([op], resetXformStack=True)
            op.Set(m)
        snap.GetRootLayer().Save()
    print(json.dumps({"assessment": str(out / "assessment.json"), "useful_operation_pass": report["useful_operation_pass"],
                      "conditions": checks, "final_minimum": report["final_interval_minimum"],
                      "final_maximum": report["final_interval_maximum"], "motor_disabled_prediction": prediction}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    assess(args.result.resolve(), args.out.resolve(), args.design.resolve(), args.control)


if __name__ == "__main__":
    main()
