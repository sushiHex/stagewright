"""Freeze a candidate, run the isolated physics worker, and export its recorded replay."""
import argparse
import json
import os
from pathlib import Path
import subprocess

import numpy as np
from pxr import Usd, UsdGeom

from physics_usd import pack, export


def measure(recording, scale):
    with np.load(recording / "poses.npz", allow_pickle=False) as poses:
        positions = poses["poses"][..., :3]
        travel = np.linalg.norm(positions-positions[0], axis=2).max(axis=0) * scale
        quaternions = poses["poses"][..., 3:]
        quaternions = quaternions / np.linalg.norm(quaternions, axis=2, keepdims=True)
        cosine = np.clip(np.abs((quaternions*quaternions[0]).sum(axis=2)), 0, 1)
        angles = np.degrees(2*np.arccos(cosine)).max(axis=0)
        return [{"path": str(path), "max_translation_m": float(distance),
                 "max_rotation_degrees": float(angle)}
                for path, distance, angle in zip(poses["paths"], travel, angles, strict=True)]


def execute(source, destination, physics_python, steps=360, fps=120):
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    scratch = destination / "scratch"
    scratch.mkdir()
    package = destination / "input.usdz"
    pack(source, package)
    worker = Path(__file__).with_name("simulate.py")
    recording = destination / "recording"
    result = subprocess.run([str(physics_python), "-I", str(worker), str(package),
                             "--out", str(recording), "--steps", str(steps), "--fps", str(fps)],
                            capture_output=True, text=True,
                            env={**os.environ, "TMPDIR": str(scratch),
                                 "TEMP": str(scratch), "TMP": str(scratch)})
    (destination / "worker.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Physics worker failed; read {destination / 'worker.log'}")
    replay = export(recording)
    stage = Usd.Stage.Open(str(package))
    scale = UsdGeom.GetStageMetersPerUnit(stage)
    bodies = measure(recording, scale)
    record = json.loads((recording / "result.json").read_text())
    feedback = {"replay": str(replay), "recording": str(recording),
                "pose_devices": record["pose_devices"], "bodies": bodies}
    (destination / "feedback.json").write_text(json.dumps(feedback, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(feedback))
    return feedback


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--physics-python", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=360)
    parser.add_argument("--fps", type=int, default=120)
    args = parser.parse_args()
    execute(args.source, args.destination, args.physics_python, args.steps, args.fps)
