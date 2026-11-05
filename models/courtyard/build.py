"""Build COURTYARD, or compose a recorded replay with its static display scene."""
import argparse
import os
from pathlib import Path
import sys


def relative(source, directory):
    try:
        return os.path.relpath(source, directory).replace("\\", "/")
    except ValueError:
        return source.as_posix()


def view(output, replay=None):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdRender

    source = output / "saves/08_logistics.usda" if replay is None else replay.resolve(strict=True)
    destination = output / ("scene.usda" if replay is None else "motion.usda")
    if destination.exists():
        raise FileExistsError(destination)
    original = Usd.Stage.Open(str(source))
    stage = Usd.Stage.CreateInMemory()
    for key in ("defaultPrim", "upAxis", "metersPerUnit", "kilogramsPerUnit",
                "timeCodesPerSecond", "framesPerSecond", "startTimeCode", "endTimeCode"):
        if original.HasAuthoredMetadata(key):
            stage.SetMetadata(key, original.GetMetadata(key))
    layers = [source] if replay is None else [source, (output / "scene.usda").resolve(strict=True)]
    stage.GetRootLayer().subLayerPaths = [path.as_posix() for path in layers]
    if replay is None:
        stage.SetTimeCodesPerSecond(24)
        stage.SetFramesPerSecond(24)
        camera = UsdGeom.Camera.Define(stage, "/World/Cameras/Comparison")
        camera.CreateClippingRangeAttr(Gf.Vec2f(.1, 1000))
        camera.CreateFocalLengthAttr(43)
        camera.CreateHorizontalApertureAttr(36)
        camera.CreateVerticalApertureAttr(20.25)
        camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(
            Gf.Vec3d(88, -110, 65), Gf.Vec3d(0, 2, -1), Gf.Vec3d(0, 0, 1)).GetInverse())
        UsdGeom.Scope.Define(stage, "/Render")
        product = UsdRender.Product.Define(stage, "/Render/Review")
        product.CreateCameraRel().SetTargets([camera.GetPath()])
        product.CreateResolutionAttr(Gf.Vec2i(1920, 1080))
        for name, kind, value in (("deviceIds", Sdf.ValueTypeNames.UIntArray, [0]),
                                  ("omni:rtx:pt:samplesPerIteration", Sdf.ValueTypeNames.Int, 4),
                                  ("omni:rtx:pt:samplesPerPixel", Sdf.ValueTypeNames.UInt, 128),
                                  ("omni:rtx:rendermode", Sdf.ValueTypeNames.Token, "PathTracing")):
            product.GetPrim().CreateAttribute(name, kind).Set(value)
        color = UsdRender.Var.Define(stage, "/Render/Review/Color")
        color.CreateSourceNameAttr("LdrColor")
        color.GetPrim().CreateAttribute("omni:rtx:aov", Sdf.ValueTypeNames.Opaque)
        product.CreateOrderedVarsRel().SetTargets([color.GetPath()])
        stage.GetRootLayer().documentation = "COURTYARD. Rebuilt scene with a fixed display camera."
    else:
        stage.GetRootLayer().documentation = "Recorded mechanism motion with static additions. No new physical evaluation of the additions."
    layer = Sdf.Layer.CreateAnonymous()
    layer.TransferContent(stage.GetRootLayer())
    layer.subLayerPaths = [relative(path, output) for path in layers]
    if not layer.Export(str(destination)):
        raise RuntimeError(f"Cannot write {destination}")
    return destination


def build(output):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from source import author, common, build_kit, fabrication, metrology, control_gallery, logistics

    output.mkdir(parents=True, exist_ok=False)
    author.configure(output)
    common.configure(output)
    for step in (author.site, author.spine, author.mechanism, author.detail,
                 build_kit.build, fabrication.build, metrology.build, control_gallery.build, logistics.build):
        step()
    return view(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new build directory, or an existing build with --replay")
    parser.add_argument("--replay", type=Path, help="recorded replay to compose as motion.usda; does not rebuild or simulate")
    args = parser.parse_args()
    output = args.out.resolve()
    print(build(output) if args.replay is None else view(output, args.replay))


if __name__ == "__main__":
    main()
