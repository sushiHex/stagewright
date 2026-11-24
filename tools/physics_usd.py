"""Bundle physics input or export recorded poses, using the author Python.

The replay composes the original scene without changing it. Recorded world
frames reset inheritance so parent transforms cannot be applied twice.
"""
import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdUtils


def _install_new(temporary, destination):
    # Windows rename fails if the target exists. POSIX rename would overwrite it.
    if os.name == "nt":
        temporary.rename(destination)
    else:
        os.link(temporary, destination)


def export_new_layer(layer, destination):
    temporary = destination.with_name(f"_{uuid.uuid4().hex}{destination.suffix}")
    try:
        if not layer.Export(str(temporary)):
            raise RuntimeError("USD layer export failed")
        _install_new(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def pack(source, destination):
    source, destination = source.resolve(strict=True), destination.resolve()
    if destination.suffix.lower() != ".usdz":
        raise ValueError("Physics packages use .usdz")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _, assets, unresolved = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(str(source)))
    if unresolved or any(Path(asset).is_dir() for asset in assets):
        raise ValueError("Physics input has unresolved or directory asset dependencies")
    temporary = destination.with_name(f"_{uuid.uuid4().hex}.usdz")
    try:
        # Native USD packaging retains composition and bundles dependencies.
        if not UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(source)), str(temporary)):
            raise RuntimeError("USD dependency packaging failed")
        _install_new(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Frozen physics input -> {destination}")


def export(recording):
    recording = recording.resolve()
    record = json.loads((recording / "result.json").read_text(encoding="utf-8"))
    source = Path(record["source"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
        raise RuntimeError("Source no longer matches the recorded scene")
    destination = recording / "replay.usdc"
    if destination.exists():
        raise FileExistsError(destination)
    # Build in memory: failed validation must not leave a replay on disk.
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths = [source.as_posix()]
    original = Usd.Stage.Open(str(source))
    for key in ("upAxis", "metersPerUnit", "kilogramsPerUnit", "defaultPrim"):
        if original.HasAuthoredMetadata(key):
            stage.SetMetadata(key, original.GetMetadata(key))
    fps = float(record["fps"])
    if not np.isfinite(fps) or fps <= 0 or record["quaternion_order"] != "xyzw":
        raise ValueError("Expected a positive tick rate and xyzw quaternions")
    stage.SetTimeCodesPerSecond(fps)
    with np.load(recording / "poses.npz", allow_pickle=False) as data:
        paths, poses, seconds = data["paths"], data["poses"], data["seconds"]
        if paths.ndim != 1 or not paths.size or len(set(paths)) != len(paths):
            raise ValueError("Expected distinct recorded body paths")
        if seconds.ndim != 1 or not seconds.size or poses.shape != (seconds.size, paths.size, 7):
            raise ValueError("Pose dimensions do not match the sample times and body paths")
        times = seconds.astype(np.float64) * fps
        if not np.isfinite(times).all() or (np.diff(times) <= 0).any():
            raise ValueError("Expected finite, strictly increasing sample times")
        rotations = poses[..., 3:].astype(np.float64)
        lengths = np.linalg.norm(rotations, axis=2, keepdims=True)
        if not np.isfinite(poses).all() or not np.isfinite(lengths).all() or (lengths == 0).any():
            raise ValueError("Expected finite poses and nonzero quaternions")
        rotations /= lengths
        stage.SetStartTimeCode(float(times[0]))
        stage.SetEndTimeCode(float(times[-1]))
        xforms = {}
        for path in paths:
            prim = original.GetPrimAtPath(str(path))
            if not prim or not prim.IsA(UsdGeom.Xformable):
                raise RuntimeError(f"Missing transformable recorded body: {path}")
            # A world-space physics frame cannot retain authored scale/shear.
            matrix = UsdGeom.XformCache().GetLocalToWorldTransform(prim)
            scale = Gf.Transform(matrix).GetScale()
            if not Gf.IsClose(scale, Gf.Vec3d(1), 1e-5):
                raise ValueError(f"Replay currently requires unit-scale body frames: {path}")
            parent = prim
            while parent and not parent.IsPseudoRoot():
                parent_xform = UsdGeom.Xformable(parent)
                if parent_xform and parent_xform.GetTimeSamples():
                    raise ValueError(f"Animated source body frames are unsupported: {path}")
                parent = parent.GetParent()
            xform = UsdGeom.Xformable(stage.GetPrimAtPath(str(path)))
            op = xform.AddTransformOp(opSuffix="physicsReplay")
            # Reset the stack: these samples are world poses, independent of parents.
            xform.SetXformOpOrder([op], resetXformStack=True)
            xforms[str(path)] = op
        for time, sample, quats in zip(times, poses, rotations, strict=True):
            for path, pose, quat in zip(paths, sample, quats, strict=True):
                x, y, z, w = map(float, quat)
                transform = Gf.Matrix4d().SetRotate(Gf.Quatd(w, Gf.Vec3d(x, y, z)))
                transform.SetTranslateOnly(Gf.Vec3d(*map(float, pose[:3])))
                xforms[str(path)].Set(transform, time)
    layer = Sdf.Layer.CreateAnonymous()
    layer.TransferContent(stage.GetRootLayer())
    layer.subLayerPaths = [os.path.relpath(source, recording).replace("\\", "/")]
    export_new_layer(layer, destination)
    print(f"Recorded USD replay -> {destination}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    bundle = commands.add_parser("pack", help="bundle a scene and dependencies into USDZ")
    bundle.add_argument("source", type=Path)
    bundle.add_argument("destination", type=Path)
    replay = commands.add_parser("replay", help="export the recorded poses as USD")
    replay.add_argument("recording", type=Path)
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.source, args.destination)
    else:
        export(args.recording)
