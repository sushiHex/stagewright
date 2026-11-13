"""Direct, procedural OpenUSD authoring. Run successive construction steps once.

All units are metres, Z is up. Each finished layer and composed save is immutable.
No authored time samples. Only tools/engine.py may produce mechanism motion.
"""
import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdPhysics, UsdLux, Vt

ROOT = None
P = json.loads(Path(__file__).with_name("parameters.json").read_text(encoding="utf-8"))
COLORS = {
    "concrete": ((0.43, 0.48, 0.52), 0.9, 0.0),
    "lightConcrete": ((0.66, 0.70, 0.72), 0.85, 0.0),
    "darkConcrete": ((0.20, 0.25, 0.29), 0.92, 0.0),
    "steel": ((0.49, 0.58, 0.64), 0.38, 0.7),
    "silver": ((0.73, 0.80, 0.83), 0.28, 0.8),
    "graphite": ((0.065, 0.09, 0.12), 0.52, 0.45),
    "orange": ((0.95, 0.22, 0.035), 0.32, 0.45),
    "blue": ((0.035, 0.25, 0.70), 0.32, 0.45),
    "blueLight": ((0.14, 0.52, 0.88), 0.32, 0.4),
    "white": ((0.86, 0.90, 0.88), 0.6, 0.1),
    "rubber": ((0.018, 0.026, 0.035), 0.84, 0.0),
    "glass": ((0.10, 0.26, 0.33), 0.12, 0.65),
    "lamp": ((0.80, 0.90, 1.0), 0.25, 0.2),
    "amber": ((1.0, 0.41, 0.06), 0.35, 0.1),
    "soil": ((0.16, 0.19, 0.18), 1.0, 0.0),
    "plant": ((0.23, 0.31, 0.26), 0.95, 0.0),
}


def configure(output):
    """Set the destination for generated layers, assets and saved stages."""
    global ROOT
    ROOT = Path(output).resolve()


def new_stage(path):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Preserved output already exists: {path}")
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    stage.GetRootLayer().documentation = "COURTYARD / NORTH LIFT. Procedural geometry. Metres, Z up."
    return stage


def material(stage, name):
    path = "/World/Looks/" + name
    mat = UsdShade.Material.Get(stage, path)
    if mat:
        return mat
    color, roughness, metallic = COLORS[name]
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, path + "/Surface")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    if name in ("lamp", "amber"):
        sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color) * 2)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return mat


def finish(stage, prim, mat):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material(stage, mat))
    UsdGeom.Gprim(prim).CreateDisplayColorAttr([Gf.Vec3f(*COLORS[mat][0])])
    return prim


def xform(stage, path, pos=(0, 0, 0), rotation=None):
    x = UsdGeom.Xform.Define(stage, path)
    x.AddTranslateOp().Set(Gf.Vec3d(*pos))
    if rotation is not None:
        x.AddOrientOp().Set(Gf.Quatf(rotation.GetQuat()))
    return x.GetPrim()


def box(stage, path, pos, size, mat, rotation=None, collision=False):
    g = UsdGeom.Cube.Define(stage, path)
    g.CreateSizeAttr(1.0)
    g.AddTranslateOp().Set(Gf.Vec3d(*pos))
    if rotation is not None:
        g.AddOrientOp().Set(Gf.Quatf(rotation.GetQuat()))
    g.AddScaleOp().Set(Gf.Vec3f(*size))
    if collision:
        UsdPhysics.CollisionAPI.Apply(g.GetPrim())
    return finish(stage, g.GetPrim(), mat)


def cylinder(stage, path, pos, radius, length, mat, axis="Z", collision=False):
    g = UsdGeom.Cylinder.Define(stage, path)
    g.CreateAxisAttr(axis)
    g.CreateRadiusAttr(radius)
    g.CreateHeightAttr(length)
    g.AddTranslateOp().Set(Gf.Vec3d(*pos))
    if collision:
        UsdPhysics.CollisionAPI.Apply(g.GetPrim())
    return finish(stage, g.GetPrim(), mat)


def sphere(stage, path, pos, scale, mat):
    g = UsdGeom.Sphere.Define(stage, path)
    g.CreateRadiusAttr(1)
    g.AddTranslateOp().Set(Gf.Vec3d(*pos))
    g.AddScaleOp().Set(Gf.Vec3f(*scale))
    return finish(stage, g.GetPrim(), mat)


def beam(stage, path, a, b, width, depth, mat):
    a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
    delta = b - a
    return box(stage, path, (a + b) * 0.5, (width, depth, delta.GetLength()), mat,
               Gf.Rotation(Gf.Vec3d(0, 0, 1), delta.GetNormalized()))


def tube(stage, path, a, b, radius, mat):
    a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
    g = UsdGeom.Cylinder.Define(stage, path)
    g.CreateRadiusAttr(radius)
    g.CreateHeightAttr((b - a).GetLength())
    g.AddTranslateOp().Set((a + b) * 0.5)
    g.AddOrientOp().Set(Gf.Quatf(Gf.Rotation(Gf.Vec3d(0, 0, 1), (b - a).GetNormalized()).GetQuat()))
    return finish(stage, g.GetPrim(), mat)


def mesh(stage, path, points, faces, mat):
    g = UsdGeom.Mesh.Define(stage, path)
    g.CreatePointsAttr(points)
    g.CreateFaceVertexCountsAttr([len(f) for f in faces])
    g.CreateFaceVertexIndicesAttr([i for face in faces for i in face])
    g.CreateSubdivisionSchemeAttr("none")
    g.CreateDoubleSidedAttr(True)
    return finish(stage, g.GetPrim(), mat)


def ribbon(stage, path, points, width, mat):
    vertices, faces = [], []
    for a, b in zip(points[:-1], points[1:]):
        a, b = np.array(a, float), np.array(b, float)
        v = b - a
        n = np.array([-v[1], v[0], 0.0])
        n *= width / (2 * np.linalg.norm(n))
        k = len(vertices)
        vertices.extend([a + n, a - n, b - n, b + n])
        faces.append([k, k+1, k+2, k+3])
    return mesh(stage, path, [tuple(v) for v in vertices], faces, mat)


# Original compact technical lettering, no font assets.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "/": ["00001", "00001", "00010", "00100", "01000", "10000", "10000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
}


def label(stage, path, text, origin, height, mat="white", plane="XZ"):
    cell = height / 7
    points, faces = [], []
    ox, oy, oz = origin
    for ci, ch in enumerate(text.upper()):
        for row, line in enumerate(FONT.get(ch, ["00000"] * 7)):
            for col, lit in enumerate(line):
                if lit == "0":
                    continue
                u = (ci * 6 + col) * cell
                v = (6 - row) * cell
                k = len(points)
                for du, dv in [(0, 0), (.88, 0), (.88, .88), (0, .88)]:
                    if plane == "XY":
                        points.append((ox + u + du*cell, oy + v + dv*cell, oz))
                    else:
                        points.append((ox + u + du*cell, oy, oz + v + dv*cell))
                faces.append([k, k+1, k+2, k+3])
    prim = mesh(stage, path, points, faces, mat)
    prim.SetCustomDataByKey("text", text)
    return prim


def reference(stage, path, asset, pos=(0, 0, 0), rotate=0, scale=None):
    prim = xform(stage, path, pos, Gf.Rotation(Gf.Vec3d(0, 0, 1), rotate))
    kit = "kit_v2.usda" if (ROOT / "assets/kit_v2.usda").exists() else "kit.usda"
    prim.GetReferences().AddReference("../assets/" + kit, "/World/" + asset)
    if scale is not None:
        UsdGeom.Xformable(prim).AddScaleOp().Set(Gf.Vec3f(*scale))
    prim.SetInstanceable(True)
    return prim


def make_kit():
    stage = new_stage("assets/kit.usda")
    for key in COLORS:
        material(stage, key)
    # Assets bind materials through the shared world palette when referenced.
    root = "/World/Bollard"
    xform(stage, root)
    cylinder(stage, root+"/Foot", (0, 0, .035), .24, .07, "graphite")
    cylinder(stage, root+"/Post", (0, 0, .52), .10, .96, "steel")
    cylinder(stage, root+"/Band", (0, 0, .83), .105, .13, "white")
    cylinder(stage, root+"/Cap", (0, 0, 1.02), .11, .045, "orange")
    root = "/World/Bolt"
    xform(stage, root)
    cylinder(stage, root+"/Washer", (0, 0, 0), .06, .016, "silver")
    cylinder(stage, root+"/Head", (0, 0, .024), .04, .036, "graphite")
    root = "/World/Bench"
    xform(stage, root)
    for i in range(5):
        box(stage, root+f"/Slat{i}", (0, -.23+i*.115, .48), (2.0, .09, .07), "silver")
    for i, x in enumerate([-.72, .72]):
        box(stage, root+f"/Leg{i}", (x, 0, .23), (.09, .46, .46), "graphite")
    root = "/World/Cabinet"
    xform(stage, root)
    box(stage, root+"/Case", (0, 0, .95), (1.1, .55, 1.9), "steel")
    box(stage, root+"/Door", (0, -.285, 1.0), (1.0, .035, 1.7), "graphite")
    box(stage, root+"/Stripe", (0, -.31, 1.72), (1.0, .014, .08), "blue")
    box(stage, root+"/Handle", (.36, -.34, .95), (.028, .04, .22), "silver")
    for i in range(6):
        box(stage, root+f"/Vent{i}", (0, -.313, .3+i*.055), (.75, .012, .012), "silver")
    stage.GetRootLayer().Save()


def cameras(stage):
    for name, eye, target, focal in [
        ("Wide", (52, -65, 40), (0, 0, 10), 43),
        ("South", (0, -66, 22), (0, 1, 12), 43),
        ("Linkage", (56, -4, 21), (0, 0, 11), 44),
        ("Human", (-24, -28, 5.5), (-3, 2, 5), 30),
    ]:
        cam = UsdGeom.Camera.Define(stage, "/World/Cameras/" + name)
        matrix = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1)).GetInverse()
        cam.AddTransformOp().Set(matrix)
        cam.CreateFocalLengthAttr(focal)
        cam.CreateHorizontalApertureAttr(36)
        cam.CreateVerticalApertureAttr(24)
        cam.CreateClippingRangeAttr(Gf.Vec2f(.1, 1000))
    light = UsdLux.DistantLight.Define(stage, "/World/Lighting/Sun")
    light.CreateIntensityAttr(2300)
    light.CreateAngleAttr(1.5)
    light.AddRotateXYZOp().Set(Gf.Vec3f(30, -26, -32))
    dome = UsdLux.DomeLight.Define(stage, "/World/Lighting/Fill")
    dome.CreateIntensityAttr(450)
    dome.CreateColorAttr(Gf.Vec3f(.73, .84, 1.0))


def site():
    make_kit()
    stage = new_stage("layers/01_site.usda")
    for key in COLORS:
        material(stage, key)
    root = "/World/Site"
    box(stage, root+"/Terrain", (0, 0, -.75), (76, 66, 1), "darkConcrete")
    box(stage, root+"/Plinth", (0, 0, -.31), (53, 46, .6), "lightConcrete", collision=True)
    box(stage, root+"/CourtBed", (0, 0, -.10), (27, 20, .2), "darkConcrete")
    # Deliberately broad paved joints, distinct from painted court outlines.
    for i in range(9):
        for j in range(7):
            x, y = -24+i*6, -20+j*6
            box(stage, root+f"/Paving/P{i}_{j}", (x, y, -.033), (5.97, 5.97, .06),
                "concrete" if (i+j)%4 else "lightConcrete")
    box(stage, root+"/CourtFinish", (0, -.5, -.013), (25.6, 19, .026), "darkConcrete")
    for s in [-1, 1]:
        box(stage, root+f"/Drain{s+1}", (s*13.35, -1, .01), (.25, 24, .02), "graphite")
        for n in range(96):
            box(stage, root+f"/Grates{s+1}/G{n}", (s*13.35, -12.8+n*.25, .026), (.23, .025, .024), "silver")
    mark = "/World/Markings"
    ribbon(stage, mark+"/CourtC01", [(-10,-8,.023),(10,-8,.023),(10,4,.023),(-10,4,.023),(-10,-8,.023)], .10, "white")
    for x in [-4,4]:
        ribbon(stage, mark+f"/Entry{x+4}", [(x,-22,.025),(x,-8,.025)], .14, "white")
    for i in range(7):
        box(stage, mark+f"/CenterDash{i}", (0, -21+i*1.8, .027), (.09, .75, .012), "white")
    for i in range(12):
        box(stage, mark+f"/Station{i}", (-10.45, -7.5+i, .027), (.35, .035, .012), "blueLight")
    for i, radius in enumerate([3, 5.5, 8]):
        points = [(radius*math.cos(t), -2+radius*math.sin(t), .024) for t in np.linspace(0,2*math.pi,129)]
        ribbon(stage, mark+f"/TurningCircle{i}", points, .045, "concrete")
    label(stage, mark+"/C01", "C01", (-8.7, -7, .035), .9, plane="XY")
    label(stage, mark+"/Approach", "PROVING COURT", (-7, -20.5, .035), .95, plane="XY")
    label(stage, mark+"/Entry", "01 / NORTH", (5.7, -14, .035), .52, plane="XY")
    for side in [-1, 1]:
        for i in range(8):
            reference(stage, root+f"/Bollards/B{side+1}_{i}", "Bollard", (side*21, -19+i*4.5, 0))
        for i in range(3):
            box(stage, root+f"/Terrace{side+1}_{i}", (side*(26.8+i*.38), 2, -.13-i*.14), (.75, 39, .22), "lightConcrete")
    for i in range(8):
        box(stage, root+f"/ApronJoints{i}", (0,-22-i*1.3,-.23), (16,.025,.04), "graphite")
    cameras(stage)
    stage.GetRootLayer().Save()
    compose("saves/01_ground.usda", ["01_site.usda"], "01 | Court foundations and proving marks")


def compose(path, layers, description):
    stage = new_stage(path)
    stage.GetRootLayer().subLayerPaths = ["../layers/"+layer for layer in reversed(layers)]
    stage.GetRootLayer().customLayerData = {"constructionStep": description, "preferredCamera": "/World/Cameras/Wide"}
    stage.GetRootLayer().Save()


def localize_kit():
    """Keep material targets inside each referenced asset's namespace."""
    dest = ROOT / "assets/kit_v2.usda"
    if dest.exists():
        raise FileExistsError(dest)
    original = Sdf.Layer.FindOrOpen(str(ROOT / "assets/kit.usda"))
    layer = Sdf.Layer.CreateNew(str(dest))
    layer.TransferContent(original)
    stage = Usd.Stage.Open(layer)
    for component in ["Bollard", "Bolt", "Bench", "Cabinet"]:
        root = "/World/" + component
        Sdf.CopySpec(layer, Sdf.Path("/World/Looks"), layer, Sdf.Path(root + "/Looks"))
        for prim in list(Usd.PrimRange(stage.GetPrimAtPath(root))):
            rel = prim.GetRelationship("material:binding")
            if rel and rel.GetTargets():
                name = rel.GetTargets()[0].name
                rel.SetTargets([Sdf.Path(root + "/Looks/" + name)])
    layer.Save()


def railing(stage, path, a, b, height=1.1):
    a, b = np.array(a, float), np.array(b, float)
    count = max(1, math.ceil(np.linalg.norm(b-a)/1.5))
    for i, t in enumerate(np.linspace(0,1,count+1)):
        p = a*(1-t)+b*t
        tube(stage, path+f"/Post{i}", p, p+[0,0,height], .025, "silver")
    for i, h in enumerate([.5,height]):
        tube(stage, path+f"/Rail{i}", a+[0,0,h], b+[0,0,h], .025, "silver")
    beam(stage, path+"/Toe", a+[0,0,.1], b+[0,0,.1], .04, .15, "graphite")


def spine():
    localize_kit()
    stage = new_stage("layers/02_spine.usda")
    for side in [-1,1]:
        for i in range(8):
            prim = stage.OverridePrim(f"/World/Site/Bollards/B{side+1}_{i}")
            prim.GetReferences().ClearReferences()
            prim.GetReferences().AddReference("../assets/kit_v2.usda", "/World/Bollard")
    root = "/World/Spine"
    box(stage, root+"/ServiceBase", (0,12.8,.12), (27,6.6,.24), "lightConcrete")
    box(stage, root+"/ServiceVolume", (0,13.4,2.7), (25,5.6,5.4), "concrete")
    box(stage, root+"/Coping", (0,13.4,5.48), (25.6,6.1,.20), "silver")
    for i in range(13):
        x = -12+i*2
        box(stage, root+f"/Facade/Fins{i}", (x,10.53,3.3), (.065,.18,4.1), "steel")
        box(stage, root+f"/Clerestory/P{i}", (x,10.51,4.5), (1.88,.06,1.15), "glass")
    for bay, x in enumerate([-8,0,8]):
        box(stage, root+f"/Bay{bay}/Frame", (x,10.46,1.8), (5.5,.18,3.6), "graphite")
        for i in range(18):
            box(stage, root+f"/Bay{bay}/Shutter{i}", (x,10.33,.2+i*.18), (5.1,.08,.16), "steel")
        box(stage, root+f"/Bay{bay}/Header", (x,10.29,3.62), (5.6,.2,.25), "graphite")
        label(stage, root+f"/Bay{bay}/Sign", ["01 / MACHINE", "02 / SERVICE", "03 / CONTROL"][bay], (x-2.35,10.17,3.49), .23)
    box(stage, root+"/Canopy", (0,9.87,5.18), (25.6,1.5,.14), "steel")
    for side in [-1,1]:
        p = root+f"/BearingTower{side+1}"
        x = side*13.3
        box(stage,p+"/Footing",(x,9.65,.3),(3.3,4.2,.6),"lightConcrete")
        box(stage,p+"/Pedestal",(x,9.7,4.45),(1.25,2.15,8.3),"concrete")
        for a in [-.72,.72]:
            box(stage,p+f"/Column{int((a+1)*10)}",(x+a,9.1,4.7),(.24,1.05,8.8),"steel")
        box(stage,p+"/Crown",(x,9.15,9.15),(2.4,2.0,.36),"silver")
        beam(stage,p+"/Buttress",(x,9.7,7.5),(x+side*2.4,13.5,.5),.8,.8,"lightConcrete")
        for z in [P["lower_pivot_z_m"], P["lower_pivot_z_m"]+P["pivot_spacing_m"]]:
            k = int(z*10)
            box(stage,p+f"/BearingBlock{k}",(x,9,z),(.6,1.25,1.25),"graphite")
            cylinder(stage,p+f"/BearingRim{k}",(x-side*.4,9,z),.58,.18,"silver","X")
            cylinder(stage,p+f"/BearingBore{k}",(x-side*.52,9,z),.30,.20,"graphite","X")
            for i in range(8):
                a = i*math.pi/4
                cylinder(stage,p+f"/CapScrew{k}_{i}",(x-side*.51,9+.46*math.sin(a),z+.46*math.cos(a)),.047,.09,"steel","X")
        label(stage,p+"/TowerID",f"N{side+2}",(x-.4,8.58,6.3),.7,"graphite")
    # Catwalk stays north of the moving roof, with a complete stair flight.
    box(stage,root+"/Catwalk",(0,14.8,5.64),(25.7,1.6,.16),"graphite")
    railing(stage,root+"/NorthRail",(-12.8,15.55,5.72),(12.8,15.55,5.72))
    for i in range(54):
        box(stage,root+f"/WalkGrating/G{i}",(-12.45+i*.47,14.8,5.74),(.035,1.5,.03),"silver")
    x0, y0, steps = -17.8, 7.8, 32
    for i in range(steps):
        y = y0+i*.27
        z = (i+1)*.175
        box(stage,root+f"/Stair/Tread{i}",(x0,y,z),(1.45,.29,.08),"silver")
    for x in [x0-.66,x0+.66]:
        beam(stage,root+f"/Stair/Stringer{str(x).replace('.','_').replace('-','m')}",(x,y0-.2,.1),(x,y0+8.5,5.6),.10,.24,"graphite")
        railing(stage,root+f"/Stair/Rail{str(x).replace('.','_').replace('-','m')}",(x,y0,.18),(x,y0+8.37,5.6))
    box(stage,root+"/Stair/Landing",(-15.5,16.0,5.6),(6.0,1.4,.18),"graphite")
    railing(stage,root+"/Stair/LandingRail",(-18.5,16.65,5.7),(-12.5,16.65,5.7))
    # Service wings and human-height fitout remain outside Court C01.
    for side in [-1,1]:
        p = root+f"/ServiceWing{side+1}"
        x = side*17.0
        box(stage,p+"/Plinth",(x,2.3,.22),(4.5,9.8,.44),"lightConcrete")
        box(stage,p+"/BackWall",(x+side*1.8,2.3,1.65),(.28,9.8,2.5),"concrete")
        for i in range(4):
            reference(stage,p+f"/Cabinet{i}","Cabinet",(x, -.7+i*2.0,.44),rotate=-side*90)
        box(stage,p+"/Worktop",(x,-3.1,1.0),(3.6,.8,.12),"silver")
        for xx in [-1.4,1.4]:
            box(stage,p+f"/Leg{int((xx+2)*10)}",(x+xx,-3.1,.65),(.08,.6,.7),"graphite")
    for i in range(6):
        reference(stage,root+f"/Benches/B{i}","Bench",(-18+i*7.2,20,0),rotate=180)
    # Tall ventilation stacks, conduits and roof equipment establish scale.
    for i,x in enumerate([-9,-5,5,9]):
        cylinder(stage,root+f"/Stack{i}",(x,13.5,6.75),.29,2.5,"silver")
        cylinder(stage,root+f"/StackCap{i}",(x,13.5,8.0),.43,.16,"graphite")
        box(stage,root+f"/AirUnit{i}",(x,12,5.98),(2.2,1.2,.8),"steel")
        for j in range(10):
            box(stage,root+f"/AirUnitGrille{i}_{j}",(x-.9+j*.2,11.39,5.98),(.06,.03,.65),"graphite")
    label(stage,root+"/MainSign","NORTH LIFT",(-5.35,10.29,6.1),1.05,"white")
    box(stage,root+"/SignSupport",(0,10.4,6.75),(15,.18,2.0),"graphite")
    label(stage,root+"/SubSign","COURTYARD / 01",(-4.1,10.28,5.97),.3,"blueLight")
    stage.GetRootLayer().Save()
    compose("saves/02_spine.usda",["01_site.usda","02_spine.usda"],"02 | Bearing towers, north service spine and access")


def rigid_body(stage, name, position, dimensions, com):
    path = "/World/Mechanism/" + name
    prim = xform(stage, path, position)
    body = UsdPhysics.RigidBodyAPI.Apply(prim)
    body.CreateRigidBodyEnabledAttr(True)
    body.CreateKinematicEnabledAttr(False)
    mass = P["body_masses_kg"][name]
    m = UsdPhysics.MassAPI.Apply(prim)
    m.CreateMassAttr(mass)
    m.CreateCenterOfMassAttr(Gf.Vec3f(*com))
    x,y,z = dimensions
    inertia = (mass*(y*y+z*z)/12, mass*(x*x+z*z)/12, mass*(x*x+y*y)/12)
    m.CreateDiagonalInertiaAttr(Gf.Vec3f(*inertia))
    m.CreatePrincipalAxesAttr(Gf.Quatf(1))
    prim.AddAppliedSchema("PhysxRigidBodyAPI")
    for name_, value, type_ in [
        ("solverPositionIterationCount", 64, Sdf.ValueTypeNames.Int),
        ("solverVelocityIterationCount", 8, Sdf.ValueTypeNames.Int),
        ("linearDamping", .03, Sdf.ValueTypeNames.Float),
        ("angularDamping", .03, Sdf.ValueTypeNames.Float),
        ("sleepThreshold", 0.0, Sdf.ValueTypeNames.Float),
    ]:
        prim.CreateAttribute("physxRigidBody:"+name_, type_, custom=False).Set(value)
    prim.SetCustomDataByKey("motionRole", "only powered body" if name == "DriveYoke" else "passive constrained body")
    return path


def hinge(stage, name, body0, body1, p0, p1, limits=None):
    joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/Joints/"+name)
    if body0:
        joint.CreateBody0Rel().SetTargets([Sdf.Path(body0)])
    joint.CreateBody1Rel().SetTargets([Sdf.Path(body1)])
    joint.CreateAxisAttr("X")
    joint.CreateLocalPos0Attr(Gf.Vec3f(*p0))
    joint.CreateLocalPos1Attr(Gf.Vec3f(*p1))
    joint.CreateLocalRot0Attr(Gf.Quatf(1))
    joint.CreateLocalRot1Attr(Gf.Quatf(1))
    joint.CreateCollisionEnabledAttr(False)
    joint.CreateJointEnabledAttr(True)
    if limits:
        joint.CreateLowerLimitAttr(limits[0])
        joint.CreateUpperLimitAttr(limits[1])
    else:
        joint.CreateLowerLimitAttr(-float("inf"))
        joint.CreateUpperLimitAttr(float("inf"))
    return joint


def pin(stage, path, pos, radius=.25, length=1.0, mat="silver"):
    cylinder(stage,path+"/Axle",pos,radius,length,mat,"X")
    for i,s in enumerate([-1,1]):
        x,y,z=pos
        cylinder(stage,path+f"/Cap{i}",(x+s*length*.5,y,z),radius*1.65,.08,"graphite","X")
        cylinder(stage,path+f"/Center{i}",(x+s*(length*.5+.05),y,z),radius*.6,.05,"silver","X")
        for n in range(6):
            a=n*math.pi/3
            cylinder(stage,path+f"/Fastener{i}_{n}",(x+s*(length*.5+.05),y+radius*1.24*math.sin(a),z+radius*1.24*math.cos(a)),.034,.05,"silver","X")


def mechanism():
    stage = new_stage("layers/03_mechanism.usda")
    scene = UsdPhysics.Scene.Define(stage,"/World/PhysicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1))
    scene.CreateGravityMagnitudeAttr(P["gravity_m_s2"])
    scene.GetPrim().AddAppliedSchema("PhysxSceneAPI")
    scene.GetPrim().CreateAttribute("physxScene:solverType", Sdf.ValueTypeNames.Token, custom=False).Set("TGS")
    scene.GetPrim().CreateAttribute("physxScene:enableGPUDynamics", Sdf.ValueTypeNames.Bool, custom=False).Set(True)
    scene.GetPrim().CreateAttribute("physxScene:timeStepsPerSecond", Sdf.ValueTypeNames.UInt, custom=False).Set(P["fps"])
    rear, low, span, high = P["rear_y_m"], P["lower_pivot_z_m"], P["link_length_m"], P["lower_pivot_z_m"]+P["pivot_spacing_m"]
    yoke = rigid_body(stage,"DriveYoke",(0,rear,low),(26,span,.9),(0,-8,0))
    roof = rigid_body(stage,"Roof",(0,rear,high),(24.8,span,1.2),(0,-span/2,.1))
    wall = rigid_body(stage,"SouthWall",(0,rear-span,low),(24.8,.5,8),(0,0,4))
    # The orange lower link is a single U-shaped rigid yoke with two side trusses.
    cylinder(stage,yoke+"/TorqueShaft",(0,0,0),.24,27.5,"orange","X",collision=True)
    for side in [-1,1]:
        x = side*12.8
        p=yoke+f"/Arm{side+1}"
        box(stage,p+"/CollisionChord",(x,-span/2,0),(.3,span,.32),"orange",collision=True)
        for i,z in enumerate([-.30,.30]):
            beam(stage,p+f"/Chord{i}",(x,0,z),(x,-span,z),.22,.20,"orange")
        for i in range(12):
            y=-i*span/12
            y1=-(i+1)*span/12
            beam(stage,p+f"/Diagonal{i}",(x,y,(-1)**i*.30),(x,y1,-(-1)**i*.30),.10,.13,"orange")
            box(stage,p+f"/Web{i}",(x,y,0),(.31,.16,.64),"orange")
            for j,z in enumerate([-.22,.22]):
                cylinder(stage,p+f"/Rivet{i}_{j}",(x+side*.17,y,z),.038,.025,"silver","X")
        for i,y in enumerate([0,-span]):
            pin(stage,p+f"/Pin{i}",(x,y,0),.26,.9)
    # One exposed driven reduction disc and one stationary motor housing.
    cylinder(stage,yoke+"/DriveDisc",(14.05,0,0),.64,.24,"orange","X")
    cylinder(stage,yoke+"/DiscHub",(14.23,0,0),.24,.2,"silver","X")
    for i in range(24):
        a=2*math.pi*i/24
        box(stage,yoke+f"/GearTeeth/T{i}",(14.05,.65*math.sin(a),.65*math.cos(a)),(.24,.13,.13),"orange",Gf.Rotation(Gf.Vec3d(1,0,0),-math.degrees(a)))
    for i in range(8):
        a=i*math.pi/4
        cylinder(stage,yoke+f"/DiscBolt{i}",(14.19,.43*math.sin(a),.43*math.cos(a)),.045,.035,"graphite","X")
    static="/World/DriveStation"
    box(stage,static+"/Plinth",(15.5,rear,.2),(2.1,2.5,.4),"lightConcrete")
    cylinder(stage,static+"/Stator",(15.5,rear,low),.49,1.6,"graphite","X")
    for i in range(12):
        cylinder(stage,static+f"/CoolingRing{i}",(14.85+i*.12,rear,low),.52,.035,"steel","X")
    cylinder(stage,static+"/EndBell",(16.35,rear,low),.43,.2,"silver","X")
    box(stage,static+"/ElectricalBox",(16.5,rear+1.3,1.1),(1.1,.6,1.8),"graphite")
    label(stage,static+"/ID","M01",(16.05,rear+.98,1.1),.32,"orange")
    # Roof has longitudinal edge girders and seven transverse Warren trusses.
    box(stage,roof+"/WeatherDeck",(0,-span/2,.28),(24.7,span,.12),"steel",collision=True)
    for side in [-1,1]:
        x=side*12.25
        box(stage,roof+f"/EdgeGirder{side+1}",(x,-span/2,0),(.30,span,1.05),"blue")
        for i,y in enumerate([0,-span]):
            pin(stage,roof+f"/Bearing{side+1}_{i}",(side*12.8,y,0),.28,1.1)
    for j in range(7):
        y=-j*span/6
        p=roof+f"/RoofTrusses/T{j}"
        for i,z in enumerate([-.50,.12]):
            beam(stage,p+f"/Chord{i}",(-12,y,z),(12,y,z),.16,.16,"silver")
        for i in range(12):
            x=-12+i*2
            beam(stage,p+f"/Web{i}",(x,y,-.50 if i%2==0 else .12),(x+2,y,.12 if i%2==0 else -.50),.09,.09,"steel")
        for i in range(4):
            box(stage,p+f"/Light{i}",(-9+i*6,y,-.61),(3.5,.10,.065),"lamp")
    for i in range(8):
        x=-10.5+i*3
        for j in range(6):
            y=-1.5-j*3
            box(stage,roof+f"/RoofPanels/P{i}_{j}",(x,y,.39),(2.94,2.94,.08),"silver" if i%3 else "lightConcrete")
            # Raised folded roof lights read as a repeated sawtooth rhythm.
            if i in [1,3,5,7]:
                p=roof+f"/RoofLights/L{i}_{j}"
                points=[(x-.75,y-1.2,.46),(x+.75,y-1.2,.46),(x+.75,y+1.2,.46),(x-.75,y+1.2,.46),(x-.75,y+1.2,.91),(x+.75,y+1.2,.91)]
                mesh(stage,p+"/Glazing",points,[[0,1,5,4]],"glass")
                mesh(stage,p+"/Cheeks",points,[[0,4,3],[1,2,5],[2,3,4,5]],"steel")
                beam(stage,p+"/Top",points[4],points[5],.045,.045,"silver")
    cylinder(stage,roof+"/RearHingeShaft",(0,0,0),.22,27.5,"blue","X")
    cylinder(stage,roof+"/FrontHingeShaft",(0,-span,0),.20,26.8,"blue","X")
    # South wall is the upright passive coupler, with a steel and blue facade.
    box(stage,wall+"/WallCore",(0,0,3.7),(24.5,.18,8.0),"graphite",collision=True)
    for i in range(9):
        x=-12+i*3
        box(stage,wall+f"/Mullion{i}",(x,0,3.7),(.14,.45,8.0),"blue")
    for j,z in enumerate([-.3,1.2,3.4,5.7,8]):
        box(stage,wall+f"/Rail{j}",(0,0,z),(24.8,.4,.15),"blue")
    for i in range(8):
        x=-10.5+i*3
        for j in range(3):
            z=1.7+j*2.2
            box(stage,wall+f"/Infill/P{i}_{j}",(x,-.14,z),(2.82,.1,2.02),"glass" if j==1 else "steel")
        for j in range(8):
            box(stage,wall+f"/Vent{i}_{j}",(x,-.26,.1+j*.14),(2.78,.12,.055),"blueLight")
        beam(stage,wall+f"/Brace{i}",(x-1.38,-.24,1.2),(x+1.38,-.24,7.8),.075,.09,"blue")
    for side in [-1,1]:
        for i,z in enumerate([0,8]):
            pin(stage,wall+f"/CouplerPins/P{side+1}_{i}",(side*12.8,0,z),.28,1.0,"blue")
        box(stage,wall+f"/CouplerPost{side+1}",(side*12.8,0,4),(.34,.46,8.2),"blue")
    box(stage,wall+"/SignBand",(0,-.29,6.9),(23.6,.08,1.45),"blue")
    label(stage,wall+"/Title","COURTYARD",(-7.15,-.34,6.62),.97,"white")
    label(stage,wall+"/SubTitle","NORTH LIFT / 01",(-4.25,-.34,6.28),.32,"blueLight")
    label(stage,wall+"/Number","01",(9.1,-.35,6.54),.95,"white")
    # Closed loop. Ground is the fourth link. Only this first hinge has a drive.
    drive_hinge=hinge(stage,"M01_GroundToYoke",None,yoke,(0,rear,low),(0,0,0),(-80,0))
    hinge(stage,"J02_GroundToRoof",None,roof,(0,rear,high),(0,0,0),(-85,5))
    hinge(stage,"J03_YokeToWall",yoke,wall,(0,-span,0),(0,0,0))
    hinge(stage,"J04_RoofToWall",roof,wall,(0,-span,0),(0,0,8))
    drive=UsdPhysics.DriveAPI.Apply(drive_hinge.GetPrim(),"angular")
    drive.CreateTypeAttr("force")
    drive.CreateTargetPositionAttr(P["target_angle_deg"])
    drive.CreateTargetVelocityAttr(0.0)
    drive.CreateStiffnessAttr(P["drive_stiffness"])
    drive.CreateDampingAttr(P["drive_damping"])
    drive.CreateMaxForceAttr(P["drive_max_force"])
    stage.GetRootLayer().Save()
    layers=["01_site.usda","02_spine.usda","03_mechanism.usda"]
    compose("saves/03_four_bar.usda",layers,"03 | Complete four-bar roof and south enclosure")
    compose("candidates/candidate_001.usda",layers,"Initial authored and evaluated mechanism candidate")


def make_vehicle():
    stage=new_stage("assets/proving_mule.usda")
    root="/World"
    stage.GetDefaultPrim().SetCustomDataByKey("design", "Original procedural electric proving mule. 5.1 m long, 2.6 m wide, 1.85 m high.")
    # The faceted body is authored as sections, without imported mesh data.
    sections=[(-2.5,.78,.48,.73),(-1.9,1.04,.43,.92),(-.8,1.02,.46,1.03),(1.0,1.01,.45,.97),(2.25,.92,.45,.78),(2.55,.62,.52,.65)]
    points=[]
    for y,w,b,t in sections:
        points.extend([(-w,y,b),(w,y,b),(w,y,t),(-w,y,t)])
    faces=[[3,2,1,0]]
    for i in range(len(sections)-1):
        for j in range(4):
            faces.append([4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j])
    faces.append([20,21,22,23])
    mesh(stage,root+"/Body",points,faces,"silver")
    box(stage,root+"/BatteryTray",(0,0,.48),(1.70,3.8,.22),"graphite")
    box(stage,root+"/NoseStripe",(0,1.72,.85),(.30,1.04,.025),"graphite")
    # Wedge canopy, clear silhouettes and recessed glass.
    glass=[(-.76,-1.05,1.0),(.76,-1.05,1.0),(.68,-.65,1.70),(-.68,-.65,1.70),(-.66,.55,1.70),(.66,.55,1.70),(.80,1.20,1.0),(-.80,1.20,1.0)]
    mesh(stage,root+"/Canopy",glass,[[0,1,2,3],[3,2,5,4],[4,5,6,7],[0,3,4,7],[1,6,5,2]],"glass")
    for i,(a,b) in enumerate([(glass[0],glass[3]),(glass[1],glass[2]),(glass[4],glass[7]),(glass[5],glass[6]),(glass[3],glass[4]),(glass[2],glass[5])]):
        tube(stage,root+f"/RollStructure/R{i}",a,b,.045,"graphite")
    box(stage,root+"/Roof",(0,-.05,1.72),(1.40,1.25,.055),"silver")
    cylinder(stage,root+"/Sensor",(0,-.3,1.82),.13,.14,"graphite")
    cylinder(stage,root+"/SensorBand",(0,-.3,1.85),.135,.045,"blueLight")
    for side in [-1,1]:
        box(stage,root+f"/Sill{side+1}",(side*1.03,0,.55),(.12,2.3,.20),"graphite")
        box(stage,root+f"/DoorHandle{side+1}",(side*.99,-.48,1.02),(.04,.23,.035),"graphite")
        tube(stage,root+f"/MirrorArm{side+1}",(side*.78,.75,1.22),(side*1.17,.72,1.25),.025,"graphite")
        box(stage,root+f"/Mirror{side+1}",(side*1.2,.72,1.27),(.17,.24,.12),"silver")
        for front,y in enumerate([-1.62,1.62]):
            p=root+f"/Wheels/W{side+1}_{front}"
            x=side*1.13
            # Tire with an actual hollow radial profile.
            pts=[]
            profile=[(-.18,.30),(-.18,.41),(-.12,.48),(.12,.48),(.18,.41),(.18,.30)]
            for dx,r in profile:
                for i in range(48):
                    a=i*math.pi/24
                    pts.append((x+dx,y+r*math.cos(a),.49+r*math.sin(a)))
            faces=[]
            for j in range(len(profile)):
                for i in range(48):
                    faces.append([j*48+i,j*48+(i+1)%48,((j+1)%len(profile))*48+(i+1)%48,((j+1)%len(profile))*48+i])
            mesh(stage,p+"/Tire",pts,faces,"rubber")
            cylinder(stage,p+"/Wheel",(x,y,.49),.30,.27,"graphite","X")
            cylinder(stage,p+"/Brake",(x+side*.14,y,.49),.235,.025,"steel","X")
            cylinder(stage,p+"/Hub",(x+side*.19,y,.49),.095,.065,"orange","X")
            for i in range(6):
                a=i*math.pi/3
                tube(stage,p+f"/Spoke{i}",(x+side*.18,y+.085*math.cos(a),.49+.085*math.sin(a)),(x+side*.18,y+.285*math.cos(a+.15),.49+.285*math.sin(a+.15)),.026,"silver")
            for i in range(36):
                a=i*math.pi/18
                box(stage,p+f"/Tread{i}",(x,y+.48*math.sin(a),.49+.48*math.cos(a)),(.24,.035,.028),"rubber",Gf.Rotation(Gf.Vec3d(1,0,0),-math.degrees(a)))
            tube(stage,p+"/UpperWishbone",(side*.60,y-.28,.70),(x,y,.55),.035,"steel")
            tube(stage,p+"/LowerWishbone",(side*.55,y+.25,.42),(x,y,.49),.040,"steel")
            # Thin over-wheel fender leaves the tire and suspension legible.
            pts=[]
            for xx in [x-.22,x+.22]:
                for a in np.linspace(.15,math.pi-.15,25):
                    pts.append((xx,y+.57*math.cos(a),.49+.57*math.sin(a)))
            mesh(stage,p+"/Fender",pts,[[i,i+1,i+26,i+25] for i in range(24)],"silver")
    for side in [-1,1]:
        box(stage,root+f"/Headlight{side+1}",(side*.63,2.31,.70),(.43,.06,.08),"lamp")
        box(stage,root+f"/TailLamp{side+1}",(side*.60,-2.47,.65),(.38,.04,.06),"amber")
        box(stage,root+f"/TowPoint{side+1}",(side*.52,2.42,.52),(.08,.25,.10),"orange")
    box(stage,root+"/FrontSplitter",(0,2.25,.43),(1.95,.50,.06),"graphite")
    box(stage,root+"/RearDeck",(0,-1.72,1.00),(1.65,.7,.055),"graphite")
    for i in range(9):
        box(stage,root+f"/DeckVent{i}",(-.68+i*.17,-1.72,1.04),(.06,.6,.022),"silver")
    label(stage,root+"/Number","01",(-.35,1.35,.985),.43,"graphite",plane="XY")
    label(stage,root+"/Plate","MULE 01",(-.46,-2.515,.54),.14,"white")
    stage.GetRootLayer().Save()


def make_figure():
    stage=new_stage("assets/technician.usda")
    root="/World"
    stage.GetDefaultPrim().SetCustomDataByKey("height_m",1.80)
    for side in [-1,1]:
        x=side*.105
        box(stage,root+f"/Boot{side+1}",(x,.045,.09),(.14,.29,.18),"graphite")
        tube(stage,root+f"/Shin{side+1}",(x,0,.16),(x,-.03,.52),.073,"steel")
        tube(stage,root+f"/Thigh{side+1}",(x,-.03,.52),(side*.09,0,.91),.095,"steel")
    sphere(stage,root+"/Hip",(0,0,.94),(.21,.13,.17),"graphite")
    sphere(stage,root+"/Jacket",(0,0,1.2),(.25,.155,.32),"steel")
    box(stage,root+"/ReflectiveBand",(0,-.151,1.18),(.40,.025,.055),"white")
    for side in [-1,1]:
        shoulder=(side*.23,0,1.4)
        elbow=(side*.32,-.08,1.15)
        hand=(side*.25,-.28,1.12)
        tube(stage,root+f"/UpperArm{side+1}",shoulder,elbow,.073,"steel")
        tube(stage,root+f"/Forearm{side+1}",elbow,hand,.061,"steel")
        sphere(stage,root+f"/Glove{side+1}",hand,(.065,.055,.055),"graphite")
    cylinder(stage,root+"/Neck",(0,0,1.50),.065,.13,"graphite")
    sphere(stage,root+"/Head",(0,0,1.64),(.105,.10,.13),"lightConcrete")
    sphere(stage,root+"/Helmet",(0,0,1.73),(.135,.13,.07),"orange")
    cylinder(stage,root+"/HelmetRim",(0,0,1.71),.15,.025,"orange")
    box(stage,root+"/Tablet",(0,-.30,1.10),(.33,.04,.22),"graphite",Gf.Rotation(Gf.Vec3d(1,0,0),-15))
    stage.GetRootLayer().Save()


def detail():
    make_vehicle()
    make_figure()
    stage=new_stage("layers/04_detail.usda")
    for name,asset,pos,angle in [
        ("ProvingMule","proving_mule.usda",(-6.4,-14.3,0),-16),
        ("Technician","technician.usda",(-9.2,-11.7,0),-25),
        ("Observer","technician.usda",(16.7,-4.6,.44),130),
    ]:
        prim=xform(stage,"/World/Scale/"+name,pos,Gf.Rotation(Gf.Vec3d(0,0,1),angle))
        prim.GetReferences().AddReference("../assets/"+asset,"/World")
        prim.SetInstanceable(True)
    root="/World/Details"
    # Covered service benches, folded neutral canopies and slender columns.
    for side in [-1,1]:
        p=root+f"/WingCanopy{side+1}"
        x=side*17.0
        box(stage,p+"/Roof",(x,2,3.7),(4.5,10.4,.14),"steel")
        for i,y in enumerate([-3,2,7]):
            for j,xx in enumerate([x-1.9,x+1.9]):
                box(stage,p+f"/Post{i}_{j}",(xx,y,2.04),(.10,.14,3.35),"graphite")
            box(stage,p+f"/UndersideLight{i}",(x,y,3.58),(2.8,.1,.06),"lamp")
        label(stage,p+"/BayName","FABRICATION" if side<0 else "INSTRUMENTS",(x-1.9,-3.23,3.42),.30,"graphite")
        for i in range(4):
            cylinder(stage,p+f"/AirBottle{i}",(x-1.0+i*.65,6.4,1.15),.20,1.4,"steel")
            sphere(stage,p+f"/BottleTop{i}",(x-1.0+i*.65,6.4,1.85),(.20,.20,.18),"steel")
            cylinder(stage,p+f"/Valve{i}",(x-1.0+i*.65,6.4,2.05),.06,.15,"blue")
        for i in range(5):
            box(stage,p+f"/PartsBin{i}",(x-1.3+i*.62,-3.1,1.23),(.5,.5,.35),"blue" if i%2 else "steel")
    for i,(x,y) in enumerate([(-23,-17),(23,-17),(-23,15),(23,15)]):
        p=root+f"/LightMast{i}"
        box(stage,p+"/Base",(x,y,.12),(.75,.75,.24),"lightConcrete")
        cylinder(stage,p+"/Pole",(x,y,4.1),.09,8.0,"graphite")
        box(stage,p+"/Crossarm",(x,y,8.15),(2.1,.14,.14),"silver")
        for j in [-1,1]:
            box(stage,p+f"/Head{j+1}",(x+j*.75,y,8.1),(.65,.5,.2),"graphite")
            box(stage,p+f"/Lens{j+1}",(x+j*.75,y,7.99),(.58,.43,.02),"lamp")
    # Native mesh leaves, stones and planted perimeter beds.
    rng=np.random.default_rng(41)
    for i,x in enumerate([-23.8,23.8]):
        box(stage,root+f"/Planter{i}/Curb",(x,0,.22),(1.8,24,.44),"lightConcrete")
        box(stage,root+f"/Planter{i}/Soil",(x,0,.45),(1.55,23.7,.04),"soil")
        for j in range(28):
            cx=x+rng.uniform(-.5,.5)
            cy=-11.2+j*.82
            pts=[]
            fs=[]
            for k in range(8):
                a=k*math.pi/4+rng.uniform(-.2,.2)
                h=rng.uniform(.3,.7)
                n=len(pts)
                pts.extend([(cx-.035*math.sin(a),cy+.035*math.cos(a),.47),(cx+.035*math.sin(a),cy-.035*math.cos(a),.47),(cx+.32*math.cos(a),cy+.32*math.sin(a),.47+h)])
                fs.append([n,n+1,n+2])
            mesh(stage,root+f"/Planter{i}/Tuft{j}",pts,fs,"plant")
    # Four-bar diagram is a static etched plate at human reading height.
    p=root+"/MechanismPlate"
    box(stage,p+"/Stand",(15.8,-12,1.1),(4.9,.18,2.2),"graphite")
    for i,x in enumerate([13.6,18.0]):
        box(stage,p+f"/Leg{i}",(x,-12,.6),(.10,.18,1.2),"silver")
    label(stage,p+"/Title","NORTH LIFT",(13.65,-12.10,1.82),.35)
    label(stage,p+"/Input","M01 INPUT",(15.8,-12.105,1.37),.20,"orange")
    label(stage,p+"/Roof","J02 ROOF",(15.8,-12.105,1.06),.20,"blueLight")
    label(stage,p+"/Wall","J03 WALL",(15.8,-12.105,.75),.20,"blueLight")
    label(stage,p+"/Court","C01 COURT",(15.8,-12.105,.44),.20,"white")
    for i,(a,b,mat) in enumerate([
        ((13.9,-12.13,.55),(15.25,-12.13,.55),"orange"),
        ((13.9,-12.13,1.4),(15.25,-12.13,1.4),"blue"),
        ((13.9,-12.13,.55),(13.9,-12.13,1.4),"blue"),
        ((15.25,-12.13,.55),(15.25,-12.13,1.4),"steel"),
    ]):
        tube(stage,p+f"/Diagram/Link{i}",a,b,.025,mat)
    for i,(x,z) in enumerate([(13.9,.55),(15.25,.55),(13.9,1.4),(15.25,1.4)]):
        cylinder(stage,p+f"/Diagram/Pin{i}",(x,-12.15,z),.06,.04,"silver","Y")
    # Numeric motion marks are fixed at the drive bearing, no animation.
    for i,angle in enumerate(range(0,81,10)):
        a=math.radians(angle)
        y=9-1.1*math.cos(a)
        z=.7+1.1*math.sin(a)
        cylinder(stage,root+f"/DriveIndex/Mark{i}",(14.32,y,z),.025,.02,"white","X")
    for side in [-1,1]:
        for i in range(14):
            box(stage,root+f"/SweepMarks/S{side+1}_{i}",(side*12.0,-8.5+i*1.2,.027),(.40,.16,.012),"orange")
    label(stage,root+"/WestWalk","SERVICE WALK",(-20.0,-10.5,.035),.5,"white",plane="XY")
    label(stage,root+"/CourtSize","20 X 12 M",(3.2,3.1,.035),.43,"white",plane="XY")
    # Roof details remain children of the recorded rigid frame.
    for side in [-1,1]:
        path=f"/World/Mechanism/Roof/EdgePlaque{side+1}"
        box(stage,path+"/Plate",(side*10.5,-18.08,-.06),(2.9,.07,.55),"graphite")
        label(stage,path+"/ID","J02 / ROOF",(side*10.5-1.3,-18.12,-.19),.28,"blueLight")
    stage.GetRootLayer().Save()
    layers=["01_site.usda","02_spine.usda","03_mechanism.usda","04_detail.usda"]
    compose("saves/04_workshop.usda",layers,"04 | Proving mule, technicians, workshop fitout and site detail")
    compose("candidates/candidate_002.usda",layers,"Complete detailed workshop candidate")
    control=new_stage("candidates/candidate_002_motor_disabled.usda")
    control.GetRootLayer().subLayerPaths=["./candidate_002.usda"]
    prim=control.OverridePrim("/World/Joints/M01_GroundToYoke")
    for name in ["stiffness","damping","maxForce"]:
        prim.CreateAttribute("drive:angular:physics:"+name,Sdf.ValueTypeNames.Float,custom=False).Set(0.0)
    control.GetRootLayer().documentation="Otherwise identical control. Only M01 stiffness, damping and maxForce are zero."
    control.GetRootLayer().Save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["site", "spine", "mechanism", "detail"])
    parser.add_argument("--out", type=Path, required=True, help="generated scene directory")
    args = parser.parse_args()
    configure(args.out)
    globals()[args.step]()


if __name__ == "__main__":
    main()
