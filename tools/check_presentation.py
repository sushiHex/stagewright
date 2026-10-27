"""Check authored camera motion, body framing and presentation clearances."""
import argparse
import itertools
import math
from pathlib import Path

import numpy as np
from pxr import Gf, Usd, UsdGeom

import build_present
import render_motion
from project_paths import SCENES


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def body_corners(cache, prim):
    bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    require(not bounds.IsEmpty(), f"Empty presentation body bounds: {prim.GetPath()}")
    low, high = bounds.GetMin(), bounds.GetMax()
    return [Gf.Vec3d(*point) for point in itertools.product(*zip(low, high))]


def check(path):
    config = build_present.DOLLY
    count, fps = config["frames"], config["fps"]
    require(render_motion.COUNT == count and render_motion.FPS == fps,
            "Motion renderer COUNT/FPS differs from the authored dolly")
    require(count >= 2 and fps > 0, "Dolly needs at least two frames and a positive frame rate")
    stage = Usd.Stage.Open(str(path))
    require(stage is not None, f"Could not open {path}")
    camera = UsdGeom.Camera(stage.GetPrimAtPath("/World/Cameras/Dolly"))
    body = stage.GetPrimAtPath("/World/Props/AhmedBody")
    require(bool(camera) and bool(body), "Presentation Dolly camera or Ahmed body is missing")
    step = stage.GetTimeCodesPerSecond() / fps
    expected_times = [frame * step for frame in range(count)]
    samples = UsdGeom.Xformable(camera).GetTimeSamples()
    require(len(samples) == count and np.allclose(samples, expected_times, atol=1e-9, rtol=0),
            "Authored dolly samples do not match the output frame schedule")
    require(math.isclose(stage.GetStartTimeCode(), expected_times[0], abs_tol=1e-9)
            and math.isclose(stage.GetEndTimeCode(), expected_times[-1], abs_tol=1e-9),
            "Stage start/end time does not match the dolly schedule")
    transforms = UsdGeom.XformCache()
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                              [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                              useExtentsHint=False)
    endpoints = []
    for frame, time in enumerate(expected_times):
        code = Usd.TimeCode(time)
        transforms.SetTime(code)
        bounds.SetTime(code)
        world = transforms.GetLocalToWorldTransform(camera.GetPrim())
        require(np.isfinite(np.asarray(world)).all(), f"Nonfinite camera pose at frame {frame}")
        eye = np.asarray(world.ExtractTranslation())
        expected_eye, target = build_present.dolly_pose(frame)
        require(np.allclose(eye, expected_eye, atol=1e-6, rtol=0),
                f"Authored camera position differs from configuration at frame {frame}")
        forward = np.asarray(world.TransformDir(Gf.Vec3d(0, 0, -1)))
        desired = target - eye
        require(np.linalg.norm(desired) > 0, f"Camera target coincides with eye at frame {frame}")
        forward /= np.linalg.norm(forward)
        desired /= np.linalg.norm(desired)
        require(np.allclose(forward, desired, atol=1e-8, rtol=0),
                f"Authored camera aim differs from configuration at frame {frame}")
        right = np.cross(desired, (0., 0., 1.))
        require(np.linalg.norm(right) > 0, f"Camera aim is parallel to world up at frame {frame}")
        right /= np.linalg.norm(right)
        expected_up = np.cross(right, desired)
        actual_up = np.asarray(world.TransformDir(Gf.Vec3d(0, 1, 0)))
        actual_up /= np.linalg.norm(actual_up)
        require(np.allclose(actual_up, expected_up, atol=1e-8, rtol=0),
                f"Authored camera rolls away from world up at frame {frame}")
        optics = camera.GetCamera(code)
        # Set the composed world transform explicitly so the check also handles camera rigs.
        optics.transform = world
        corners = body_corners(bounds, body)
        require(all(optics.frustum.Intersects(point) for point in corners),
                f"Presentation body leaves the camera frustum at frame {frame}")
        if frame in (0, count - 1):
            endpoints.append((eye, corners))
    margin = config["min_clearance"]
    require(margin > 0, "Dolly clearance must be positive")
    first_eye, first_corners = endpoints[0]
    last_eye, last_corners = endpoints[-1]
    require(first_eye[1] <= min(point[1] for point in first_corners) - margin,
            "Dolly must start behind the body tail with clearance")
    require(last_eye[1] >= max(point[1] for point in last_corners) + margin,
            "Dolly must finish past the body nose with clearance")
    build_present.check_dolly(path)
    build_present.check_stilts(path)
    print(f"PASS: {count} authored poses, body framing, tail-to-nose travel and clearances")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=SCENES / "present.usda")
    args = parser.parse_args()
    try:
        check(args.scene.resolve())
    except RuntimeError as error:
        parser.exit(1, f"FAIL: {error}\n")


if __name__ == "__main__":
    main()
