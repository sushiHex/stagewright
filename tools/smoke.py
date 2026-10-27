# Renderer smoke test: author a lit scene with pxr, render two camera poses with ovrtx.
#   python tools/smoke.py make
#   python tools/smoke.py render
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE = ROOT / "build" / "smoke.usda"
FRAMES = ROOT / "build" / "smoke"
COUNT = 2


def make():
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdRender, UsdShade

    s = Usd.Stage.CreateInMemory()
    s.SetDefaultPrim(UsdGeom.Xform.Define(s, "/World").GetPrim())
    UsdGeom.SetStageUpAxis(s, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(s, 0.01)
    s.SetTimeCodesPerSecond(24)
    s.SetStartTimeCode(0)
    s.SetEndTimeCode(COUNT - 1)

    floor = UsdGeom.Cube.Define(s, "/World/Floor")
    floor.CreateSizeAttr(1)
    floor.AddScaleOp().Set(Gf.Vec3f(2000, 2000, 2))
    box = UsdGeom.Cube.Define(s, "/World/Test")
    box.CreateSizeAttr(100)
    box.AddTranslateOp().Set(Gf.Vec3d(0, 0, 51))

    mat = UsdShade.Material.Define(s, "/World/Looks/Blue")
    sh = UsdShade.Shader.Define(s, "/World/Looks/Blue/Surface")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.08, 0.3, 0.65))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.35)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(box.GetPrim()).Bind(mat)

    # Off-axis marker: without it the scene is 4-fold symmetric and a 90-degree orbit looks static.
    mark = UsdGeom.Sphere.Define(s, "/World/Marker")
    mark.CreateRadiusAttr(40)
    mark.AddTranslateOp().Set(Gf.Vec3d(150, -150, 40))
    red = UsdShade.Material.Define(s, "/World/Looks/Red")
    rsh = UsdShade.Shader.Define(s, "/World/Looks/Red/Surface")
    rsh.CreateIdAttr("UsdPreviewSurface")
    rsh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.8, 0.05, 0.05))
    red.CreateSurfaceOutput().ConnectToSource(rsh.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(mark.GetPrim()).Bind(red)

    dome = UsdLux.DomeLight.Define(s, "/World/Sky")
    dome.CreateIntensityAttr(300)
    key = UsdLux.RectLight.Define(s, "/World/Key")
    key.CreateWidthAttr(300)
    key.CreateHeightAttr(300)
    key.CreateIntensityAttr(20000)
    key.AddTranslateOp().Set(Gf.Vec3d(0, 0, 400))  # faces local -Z

    cam = UsdGeom.Camera.Define(s, "/World/Camera")
    cam.CreateFocalLengthAttr(35)
    cam.CreateHorizontalApertureAttr(36)
    cam.CreateVerticalApertureAttr(20.25)
    cam.CreateClippingRangeAttr(Gf.Vec2f(1, 100000))
    pose = cam.AddTransformOp()
    for i in range(COUNT):
        a = math.pi / 4 + math.pi / 2 * i
        eye = Gf.Vec3d(450 * math.cos(a), 450 * math.sin(a), 250)
        view = Gf.Matrix4d().SetLookAt(eye, Gf.Vec3d(0, 0, 50), Gf.Vec3d(0, 0, 1))
        pose.Set(view.GetInverse(), i)

    prod = UsdRender.Product.Define(s, "/Render/Image")
    prod.CreateCameraRel().SetTargets([cam.GetPath()])
    prod.CreateResolutionAttr(Gf.Vec2i(960, 540))
    var = UsdRender.Var.Define(s, "/Render/Image/Color")
    var.CreateSourceNameAttr("LdrColor")
    prod.CreateOrderedVarsRel().SetTargets([var.GetPath()])
    p = prod.GetPrim()
    p.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token).Set("PathTracing")
    p.CreateAttribute("omni:rtx:pt:samplesPerPixel", Sdf.ValueTypeNames.UInt).Set(64)
    p.CreateAttribute("omni:rtx:pt:denoising:enabled", Sdf.ValueTypeNames.Bool).Set(True)

    SCENE.parent.mkdir(parents=True, exist_ok=True)
    s.GetRootLayer().Export(str(SCENE))
    print("wrote", SCENE)


def render():

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import rtx as rt
    from image_io import write_rgb

    FRAMES.mkdir(parents=True, exist_ok=True)
    product = "/Render/Image"
    with rt.open_renderer() as rtx, rt.loaded_scene(rtx, "smoke", SCENE) as scene:
        for i in range(COUNT):
            ordinal = i + 2  # ordinal 1 is the initial load
            rt.seek(scene, ordinal, i / 24)
            result = rtx.step(render_products={product}, ordinal=ordinal, delta_time=1 / 60)
            px = rt.pixels(rt.frame_of(result, product, index=0), f"{product}/Color")
            del result
            rgb = px[..., :3].astype(float)
            half = rgb.shape[1] // 2
            print(f"frame {i}: shape={px.shape} left={rgb[:, :half].mean():.1f} right={rgb[:, half:].mean():.1f}")
            write_rgb(FRAMES / f"{i:04d}.png", px)


if __name__ == "__main__":
    {"make": make, "render": render}[sys.argv[1]]()
