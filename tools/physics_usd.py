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
        temporary.replace(destination)
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
    stage.SetTimeCodesPerSecond(record["fps"])
    with np.load(recording / "poses.npz", allow_pickle=False) as data:
        paths, poses, seconds = data["paths"], data["poses"], data["seconds"]
        stage.SetStartTimeCode(float(seconds[0] * record["fps"]))
        stage.SetEndTimeCode(float(seconds[-1] * record["fps"]))
        xforms = {}
        for path in paths:
            prim = stage.GetPrimAtPath(str(path))
            if not prim or not prim.IsA(UsdGeom.Xformable):
                raise RuntimeError(f"Missing transformable recorded body: {path}")
            # A world-space physics frame cannot retain authored scale/shear.
            matrix = UsdGeom.XformCache().GetLocalToWorldTransform(prim)
            scale = Gf.Transform(matrix).GetScale()
            if not Gf.IsClose(scale, Gf.Vec3d(1), 1e-5):
                raise ValueError(f"Replay currently requires unit-scale body frames: {path}")
            xform = UsdGeom.Xformable(prim)
            parent = prim
            while parent and not parent.IsPseudoRoot():
                parent_xform = UsdGeom.Xformable(parent)
                if parent_xform and parent_xform.GetTimeSamples():
                    raise ValueError(f"Animated source body frames are unsupported: {path}")
                parent = parent.GetParent()
            op = xform.AddTransformOp(opSuffix="physicsReplay")
            # Reset the stack: these samples are world poses, independent of parents.
            xform.SetXformOpOrder([op], resetXformStack=True)
            xforms[str(path)] = op
        for second, sample in zip(seconds, poses, strict=True):
            time = float(second * record["fps"])
            for path, pose in zip(paths, sample, strict=True):
                x, y, z, w = map(float, pose[3:])
                transform = Gf.Matrix4d().SetRotate(Gf.Quatd(w, Gf.Vec3d(x, y, z)))
                transform.SetTranslateOnly(Gf.Vec3d(*map(float, pose[:3])))
                xforms[str(path)].Set(transform, time)
    layer = Sdf.Layer.CreateAnonymous()
    layer.TransferContent(stage.GetRootLayer())
    layer.subLayerPaths = [os.path.relpath(source, recording).replace("\\", "/")]
    temporary = destination.with_name(f"_{uuid.uuid4().hex}.usdc")
    try:
        if not layer.Export(str(temporary)):
            raise RuntimeError("USD replay export failed")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
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
