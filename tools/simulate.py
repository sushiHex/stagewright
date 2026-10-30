"""Run an authored USD scene in a separate ovphysx process and record rigid poses.

Use the isolated physics Python. Bundle input and export recordings with
physics_usd.py in the author environment. This process never imports pxr or a renderer.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np


def read_poses(physics):
    from ovphysx.types import ObjectScope, SimObjectType

    poses, devices = {}, set()
    with physics.read_sync(SimObjectType.RIGID_BODY, ["position", "orientation"],
                           scope=ObjectScope.ALL, metadata=True) as result:
        for attribute in result.metadata.attributes:
            if attribute.omission_reasons:
                raise RuntimeError(f"Incomplete pose read: {attribute}")
        for group in result.groups:
            paths = result.dictionary.get_path_strings(group.prim_list)
            name = result.dictionary.token_to_string(group.attribute)
            devices.add(str(group.tensors[0].device))
            values = group.tensors[0].numpy().copy()
            for path, value in zip(paths, values, strict=True):
                poses.setdefault(path, {})[name] = value
    if not poses or any(set(pose) != {"position", "orientation"} for pose in poses.values()):
        raise RuntimeError("No complete rigid-body poses returned")
    return poses, devices


def simulate(scene_file, output, steps, fps):
    import ovphysx
    import ovstage

    scene_file = scene_file.resolve(strict=True)
    if scene_file.suffix.lower() != ".usdz":
        raise ValueError("Bundle the input with physics_usd.py pack before simulation")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Discover codeless resources without importing their pxr-facing Python API.
    provider = importlib.metadata.distribution("physx-usd-schemas")
    schemas = [str(provider.locate_file(f).parent) for f in provider.files
               if f.name == "plugInfo.json"]
    ovstage.population.register_usd_schemas(schemas)
    stage = ovstage.Stage("physics")
    physics = None
    attached = False
    samples, paths, devices = [], None, set()
    source_hash = hashlib.sha256(scene_file.read_bytes()).hexdigest()
    try:
        ovstage.population.open_usd(stage, str(scene_file), ordinal=1,
                                   domains=ovstage.PopulationDomain.ALL)
        stage.advance_write_floor(ordinal=1).wait()
        # Pose-only worker: DirectGPU keeps simulation-state reads on CUDA.
        physics = ovphysx.PhysX(active_cuda_gpus="0", config=ovphysx.PhysXConfig(
            carbonite_overrides={"/physics/suppressReadback": True}))
        physics.wait_task(physics.attach_ovstage(stage, read_ordinal=1))
        attached = True
        for _ in range(steps):
            physics.step_sync(1 / fps)
            poses, pose_devices = read_poses(physics)
            devices.update(pose_devices)
            current_paths = sorted(poses)
            if paths is None:
                paths = current_paths
            if current_paths != paths:
                raise RuntimeError("Rigid-body membership changed during this recording")
            sample = np.array([np.r_[poses[path]["position"], poses[path]["orientation"]]
                               for path in paths])
            if not np.isfinite(sample).all():
                raise RuntimeError("Non-finite simulation pose")
            samples.append(sample)
            physics.wait_all()
    finally:
        try:
            if physics is not None:
                if attached:
                    physics.wait_task(physics.detach_ovstage())
                physics.destroy()
        finally:
            stage.destroy()
    if hashlib.sha256(scene_file.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError("Input scene changed during execution")
    np.savez(output / "poses.npz", paths=np.array(paths), poses=np.array(samples),
             seconds=np.arange(1, steps + 1, dtype=float) / fps)
    record = {"source": str(scene_file), "source_sha256": source_hash,
              "fps": fps, "samples": steps, "quaternion_order": "xyzw",
              "pose_devices": sorted(devices),
              "packages": {name: importlib.metadata.version(name) for name in
                           ("ovphysx", "ovstage", "warp-lang", "physx-usd-schemas")}}
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded rigid-body poses -> {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="new result directory")
    parser.add_argument("--steps", type=int, default=360)
    parser.add_argument("--fps", type=int, default=120, help="fixed simulation tick rate")
    args = parser.parse_args()
    if args.steps < 1 or args.fps < 1:
        parser.error("steps and fps must be positive")
    simulate(args.scene, args.out, args.steps, args.fps)
