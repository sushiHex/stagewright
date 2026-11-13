"""Static procedural workshop additions. Metres, Z up."""
from pathlib import Path
import math

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

from . import author as accepted

ROOT = None
FONT = accepted.FONT
COLORS = dict(accepted.COLORS)
COLORS["glazing"] = ((0.22, 0.34, 0.39), 0.20, 0.12)
CFG = {
    "west_hall": {"x_bounds": [-36.5, -28.5], "y_bounds": [-9.0, 18.0], "eave_z": 7.15},
    "east_hall": {"x_bounds": [28.5, 36.5], "y_bounds": [-9.0, 18.0], "eave_z": 6.8},
    "north_gallery": {"deck_z": 5.72, "y_bounds": [23.05, 25.45], "x_bounds": [-33.2, 33.2]},
    "saves": {"5": "05_fabrication.usda", "6": "06_metrology.usda",
              "7": "07_control_gallery.usda", "8": "08_logistics.usda"},
}
EXT = "/World/Expansion"


def configure(output):
    global ROOT
    ROOT = Path(output).resolve()


def fresh(path, default="World"):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Complete outputs are preserved: {path}")
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    if default:
        prim = stage.OverridePrim("/" + default)
        stage.SetDefaultPrim(prim)
    return stage


class Builder:
    def __init__(self, stage, materials=EXT + "/Looks"):
        self.stage = stage
        self.materials = materials

    def mat(self, name):
        path = self.materials + "/" + name
        mat = UsdShade.Material.Get(self.stage, path)
        if mat:
            return mat
        color, roughness, metallic = COLORS[name]
        mat = UsdShade.Material.Define(self.stage, path)
        sh = UsdShade.Shader.Define(self.stage, path + "/Surface")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
        sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
        if name == "glazing":
            sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.28)
            sh.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.45)
        if name == "lamp":
            sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color) * 0.6)
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        return mat

    def finish(self, prim, mat):
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(self.mat(mat))
        UsdGeom.Gprim(prim).CreateDisplayColorAttr([Gf.Vec3f(*COLORS[mat][0])])
        return prim

    def group(self, path, pos=None, angle=None):
        xf = UsdGeom.Xform.Define(self.stage, path)
        if pos is not None:
            xf.AddTranslateOp().Set(Gf.Vec3d(*pos))
        if angle is not None:
            xf.AddRotateZOp().Set(float(angle))
        return xf.GetPrim()

    def box(self, path, pos, size, mat="steel", rotation=None):
        assert min(size) > 0, (path, size)
        g = UsdGeom.Cube.Define(self.stage, path)
        g.CreateSizeAttr(1)
        g.CreateExtentAttr([Gf.Vec3f(-.5), Gf.Vec3f(.5)])
        g.AddTranslateOp().Set(Gf.Vec3d(*pos))
        if rotation is not None:
            g.AddOrientOp().Set(Gf.Quatf(rotation.GetQuat()))
        g.AddScaleOp().Set(Gf.Vec3f(*size))
        return self.finish(g.GetPrim(), mat)

    def cylinder(self, path, pos, radius, height, mat="silver", axis="Z", rotation=None):
        g = UsdGeom.Cylinder.Define(self.stage, path)
        g.CreateAxisAttr(axis)
        g.CreateRadiusAttr(radius)
        g.CreateHeightAttr(height)
        v = [radius] * 3
        v["XYZ".index(axis)] = height * .5
        g.CreateExtentAttr([Gf.Vec3f(*[-x for x in v]), Gf.Vec3f(*v)])
        g.AddTranslateOp().Set(Gf.Vec3d(*pos))
        if rotation is not None:
            g.AddOrientOp().Set(Gf.Quatf(rotation.GetQuat()))
        return self.finish(g.GetPrim(), mat)

    def mesh(self, path, points, faces, mat="steel"):
        assert points and faces, path
        g = UsdGeom.Mesh.Define(self.stage, path)
        g.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
        g.CreateFaceVertexCountsAttr([len(f) for f in faces])
        g.CreateFaceVertexIndicesAttr([i for f in faces for i in f])
        g.CreateSubdivisionSchemeAttr("none")
        g.CreateDoubleSidedAttr(True)
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        g.CreateExtentAttr([Gf.Vec3f(*lo), Gf.Vec3f(*hi)])
        return self.finish(g.GetPrim(), mat)

    def beam(self, path, a, b, width=.12, depth=.16, mat="steel"):
        a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
        d = b - a
        return self.box(path, (a+b)*.5, (width, depth, d.GetLength()), mat,
                        Gf.Rotation(Gf.Vec3d(0, 0, 1), d.GetNormalized()))

    def tube(self, path, a, b, radius=.028, mat="silver"):
        a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
        d = b - a
        return self.cylinder(path, (a+b)*.5, radius, d.GetLength(), mat,
                             rotation=Gf.Rotation(Gf.Vec3d(0, 0, 1), d.GetNormalized()))

    def rail(self, path, a, b, height=1.1):
        a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
        n = max(1, math.ceil((b-a).GetLength()/1.5))
        for i in range(n+1):
            q = a + (b-a)*i/n
            self.tube(path+f"/P{i:02}", q, q+Gf.Vec3d(0, 0, height), .03)
        for i, h in enumerate((.53, height)):
            d = Gf.Vec3d(0, 0, h)
            self.tube(path+f"/R{i}", a+d, b+d, .028)
        self.beam(path+"/Toe", a+Gf.Vec3d(0,0,.09), b+Gf.Vec3d(0,0,.09), .08, .12, "graphite")

    def label(self, path, text, origin, height=.3, mat="white", plane="XZ"):
        cell = height/7
        points, faces = [], []
        for ci, ch in enumerate(text.upper()):
            for row, line in enumerate(FONT.get(ch, ["00000"]*7)):
                for col, on in enumerate(line):
                    if on != "1":
                        continue
                    k = len(points)
                    u, v = (ci*6+col)*cell, (6-row)*cell
                    for du, dv in ((0,0),(.88,0),(.88,.88),(0,.88)):
                        xx, vv = u+du*cell, v+dv*cell
                        if plane == "XY":
                            points.append((origin[0]+xx, origin[1]+vv, origin[2]))
                        else:
                            points.append((origin[0]+xx, origin[1], origin[2]+vv))
                    faces.append((k,k+1,k+2,k+3))
        p = self.mesh(path, points, faces, mat)
        p.SetCustomDataByKey("text", text)
        return p

    def instance(self, path, component, pos, angle=0):
        p = self.group(path, pos, angle)
        p.GetReferences().AddReference("../assets/workshop_kit.usda", "/Kit/"+component)
        p.SetInstanceable(True)
        return p

    def role(self, prim, role):
        prim.SetCustomDataByKey("staticRole", role)
        prim.SetCustomDataByKey("simulation", "Static architectural equipment only; no new physical evaluation.")


def begin(number, slug, title, program):
    stage = fresh(f"layers/{number:02}_{slug}.usda")
    b = Builder(stage)
    b.group(EXT)
    root = EXT + f"/Pass{number:02}"
    prim = b.group(root)
    prim.SetCustomDataByKey("constructionPass", number)
    prim.SetCustomDataByKey("program", program)
    prim.SetCustomDataByKey("staticSceneEvolution", True)
    stage.GetRootLayer().documentation = title
    return stage, b, root


def save_pass(stage, number, slug, title, change):
    """Save the additive layer and compose the complete static state."""
    stage.GetRootLayer().Save()
    previous = "04_workshop.usda" if number == 5 else CFG["saves"][str(number-1)]
    filename = CFG["saves"][str(number)]
    composed = fresh("saves/"+filename)
    composed.GetRootLayer().subLayerPaths = [f"../layers/{number:02}_{slug}.usda", "./"+previous]
    composed.GetRootLayer().documentation = "COURTYARD / NORTH LIFT. Static additions. " + title
    composed.GetRootLayer().customLayerData = {
        "constructionPass": number,
        "constructionChange": change,
        "preferredCamera": "/World/Cameras/Wide",
        "motion": "Accepted mechanism unchanged. No new time samples or physics.",
    }
    composed.GetRootLayer().Save()
    print("Saved saves/" + filename)
