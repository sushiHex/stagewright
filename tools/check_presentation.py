"""Check authored camera motion, body framing, clearances and periodic loop closure."""
import argparse
import itertools
import math
from pathlib import Path

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdRender

import build_present
import render_motion
from project_paths import SCENES, MOTION_SETTINGS


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def bound_corners(cache, prim):
    bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    require(not bounds.IsEmpty(), f"Empty framing bounds: {prim.GetPath()}")
    low, high = bounds.GetMin(), bounds.GetMax()
    return [Gf.Vec3d(*point) for point in itertools.product(*zip(low, high))]


def check_orbit(positions, matrices, targets, config):
    """One full tour with unique views and continuous motion through its moving join."""
    count = config["frames"]
    require(np.array_equal(matrices[0], matrices[-1]), "Orbit closure pose differs from the first pose")
    encoded = positions[:count]
    require(len(np.unique(np.round(encoded, 8), axis=0)) == count,
            "Orbit repeats an encoded pose, including a duplicate endpoint")
    relative = positions[:, :2] - np.asarray(config["center"], float)
    angles = np.unwrap(np.arctan2(relative[:, 1], relative[:, 0]))
    increments = np.diff(angles)
    require(np.all(increments > 0) or np.all(increments < 0), "Tour reverses its winding direction")
    require(math.isclose(abs(angles[-1] - angles[0]), 2 * math.pi, abs_tol=1e-9),
            "Tour does not wind through one complete turn")
    require(np.ptp(np.linalg.norm(relative, axis=1)) > 200
            and np.ptp(positions[:, 2]) > 150 and np.ptp(targets[:, 1]) > 200,
            "Tour lost its changing distance, crane motion or environment-led aim")
    for label, points in (("eye", positions), ("aim", targets)):
        steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
        require(np.all(steps > 1e-6), f"Tour {label} pauses on an encoded pose")
        # Check the analytic curve from both sides of the wrap, independently of
        # the exact closure matrix. This catches a closed path with a velocity pop.
        h = 0.001
        sample = lambda f: build_present.orbit_pose(f)[0 if label == "eye" else 1]
        left2, left, join, right, right2 = (sample(f) for f in (-2*h, -h, 0, h, 2*h))
        require(np.allclose((join-left)/h, (right-join)/h, atol=0.001, rtol=0),
                f"Tour {label} velocity jumps at the loop boundary")
        require(np.allclose((join-2*left+left2)/h**2, (right2-2*right+join)/h**2,
                            atol=0.0001, rtol=0),
                f"Tour {label} acceleration jumps at the loop boundary")


def check_motion(stage, name, config, pose_at):
    count, fps = config["frames"], config["fps"]
    require(count >= 2 and fps > 0, f"{name} needs at least two frames and a positive frame rate")
    settings = MOTION_SETTINGS[name]
    require((count, fps, config["loop"]) == (settings["frames"], settings["fps"], settings["loop"]),
            f"{name} builder and renderer cadence differ")
    camera = UsdGeom.Camera(stage.GetPrimAtPath(f"/World/Cameras/{name}"))
    body = stage.GetPrimAtPath("/World/Props/AhmedBody")
    require(bool(camera) and bool(body), f"Presentation {name} camera or Ahmed body is missing")
    product = UsdRender.Product(stage.GetPrimAtPath(f"/Render/{name}"))
    require(bool(product) and product.GetCameraRel().GetTargets() == [camera.GetPath()],
            f"{name} render product does not target its checked camera")
    step = stage.GetTimeCodesPerSecond() / fps
    expected_times = [frame * step for frame in range(count + int(config["loop"]))]
    samples = UsdGeom.Xformable(camera).GetTimeSamples()
    require(len(samples) == len(expected_times)
            and np.allclose(samples, expected_times, atol=1e-9, rtol=0),
            f"Authored {name} samples do not match the output schedule and closure")
    transforms = UsdGeom.XformCache()
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                              [UsdGeom.Tokens.default_, UsdGeom.Tokens.render], useExtentsHint=False)
    positions, matrices, targets, endpoints = [], [], [], []
    for frame, time in enumerate(expected_times):
        code = Usd.TimeCode(time)
        transforms.SetTime(code)
        bounds.SetTime(code)
        world = transforms.GetLocalToWorldTransform(camera.GetPrim())
        matrix = np.asarray(world)
        require(np.isfinite(matrix).all(), f"Nonfinite {name} pose at frame {frame}")
        eye = np.asarray(world.ExtractTranslation())
        expected_eye, target = pose_at(frame)
        require(np.allclose(eye, expected_eye, atol=1e-6, rtol=0),
                f"Authored {name} position differs from configuration at frame {frame}")
        forward = np.asarray(world.TransformDir(Gf.Vec3d(0, 0, -1)))
        desired = target - eye
        require(np.linalg.norm(desired) > 0, f"{name} target coincides with eye at frame {frame}")
        forward /= np.linalg.norm(forward)
        desired /= np.linalg.norm(desired)
        require(np.allclose(forward, desired, atol=1e-8, rtol=0),
                f"Authored {name} aim differs from configuration at frame {frame}")
        right = np.cross(desired, (0., 0., 1.))
        require(np.linalg.norm(right) > 0, f"{name} aim is parallel to world up at frame {frame}")
        right /= np.linalg.norm(right)
        expected_up = np.cross(right, desired)
        actual_up = np.asarray(world.TransformDir(Gf.Vec3d(0, 1, 0)))
        actual_up /= np.linalg.norm(actual_up)
        require(np.allclose(actual_up, expected_up, atol=1e-8, rtol=0),
                f"Authored {name} rolls away from world up at frame {frame}")
        optics = camera.GetCamera(code)
        optics.transform = world
        require(math.isclose(optics.focalLength, config["focal"], abs_tol=1e-6)
                and math.isclose(optics.horizontalAperture, config["h_ap"], abs_tol=1e-6)
                and math.isclose(optics.verticalAperture, config["h_ap"] * 9 / 16, abs_tol=1e-6),
                f"{name} optical framing differs from configuration at frame {frame}")
        corners = bound_corners(bounds, body)
        require(all(optics.frustum.Intersects(point) for point in corners),
                f"Presentation body leaves the {name} frustum at frame {frame}")
        if config["loop"]:
            # Bound the body's screen footprint so environment context cannot
            # silently regress to a tight product orbit.
            projection = np.asarray(optics.frustum.ComputeViewMatrix() * optics.frustum.ComputeProjectionMatrix())
            clip = np.asarray([(*point, 1.0) for point in corners]) @ projection
            screen = clip[:, :2] / clip[:, 3, None]
            footprint = np.ptp(screen, axis=0) / 2
            require(np.all(footprint <= config["max_body_frame"]),
                    f"Tour environment framing too tight at frame {frame}: {footprint}")
            if frame in (0, count // 2):
                feature = "Nozzle" if frame == 0 else "CollectorFace"
                prim = stage.GetPrimAtPath(f"/World/WindTunnel/Geometry/Tunnel/{feature}")
                require(bool(prim), f"Missing environment feature: {feature}")
                feature_clip = np.asarray([(*p, 1.0) for p in bound_corners(bounds, prim)]) @ projection
                feature_screen = feature_clip[:, :2] / feature_clip[:, 3, None]
                require(np.all(feature_clip[:, 3] > 0) and np.max(np.abs(feature_screen)) <= 0.95,
                        f"Tour establishing view crops {feature}")
        positions.append(eye.copy())
        matrices.append(matrix.copy())
        targets.append(np.asarray(target).copy())
        if frame in (0, count - 1):
            endpoints.append((eye, corners))
    margin = config["min_clearance"]
    require(margin > 0, f"{name} clearance must be positive")
    if config["loop"]:
        check_orbit(np.asarray(positions), np.asarray(matrices), np.asarray(targets), config)
    else:
        first_eye, first_corners = endpoints[0]
        last_eye, last_corners = endpoints[-1]
        require(first_eye[1] <= min(point[1] for point in first_corners) - margin,
                "Dolly must start behind the body tail with clearance")
        require(last_eye[1] >= max(point[1] for point in last_corners) + margin,
                "Dolly must finish past the body nose with clearance")
    print(f"PASS: {name} authored timing, poses, aim, body framing and "
          + ("smooth cyclic closure and environment framing" if config["loop"] else "tail-to-nose travel"))


def check(path):
    stage = Usd.Stage.Open(str(path))
    require(stage is not None, f"Could not open {path}")
    motions = (("Dolly", build_present.DOLLY, build_present.dolly_pose),
               ("Orbit360", build_present.ORBIT, build_present.orbit_pose))
    require(render_motion.COUNT == build_present.DOLLY["frames"]
            and render_motion.FPS == build_present.DOLLY["fps"], "Default renderer cadence differs from Dolly")
    end_time = max((c["frames"] - 1 + int(c["loop"])) * stage.GetTimeCodesPerSecond() / c["fps"]
                   for _, c, _ in motions)
    require(math.isclose(stage.GetStartTimeCode(), 0, abs_tol=1e-9)
            and math.isclose(stage.GetEndTimeCode(), end_time, abs_tol=1e-9),
            "Stage start/end time does not contain the exact authored motion ranges")
    for name, config, pose_at in motions:
        check_motion(stage, name, config, pose_at)
        build_present.check_dolly(path, name, config)
    build_present.check_stilts(path)
    print("PASS: both presentation motions and clearances")


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
