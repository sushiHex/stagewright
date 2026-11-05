"""COURTYARD helper adapter: Exchange SDK primitives, original procedural detail."""
from pathlib import Path
import math
import usdex.core as core
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdPhysics, Vt
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from models.courtyard.source import author as courtyard

COLORS = dict(courtyard.COLORS)
COLORS.update(teal=((.025, .59, .48), .46, .3), glazing=((.15, .30, .38), .2, .15))


def stage_at(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    return core.createStage(str(path), "World", "Z", 1.0,
                            "Inspection hall / COURTYARD construction experiment", massUnits=1.0)


def material(stage, name):
    path = Sdf.Path("/World/Looks/" + name)
    mat = UsdShade.Material.Get(stage, path)
    if not mat:
        color, rough, metal = COLORS[name]
        mat = core.definePreviewMaterial(stage, path, Gf.Vec3f(*color),
                                         .22 if name == "glazing" else 1.0, rough, metal)
    return mat


def finish(stage, prim, mat):
    core.bindMaterial(prim, material(stage, mat))
    UsdGeom.Gprim(prim).CreateDisplayColorAttr([Gf.Vec3f(*COLORS[mat][0])])
    return prim


def transform(prim, pos=(0, 0, 0), rotation=None, scale=(1, 1, 1)):
    q = Gf.Quatf(1) if rotation is None else Gf.Quatf(rotation.GetQuat())
    core.setLocalTransform(prim, Gf.Vec3d(*pos), q, Gf.Vec3f(*scale))


def xform(stage, path, pos=(0, 0, 0), rotation=None):
    prim = core.defineXform(stage, Sdf.Path(path)).GetPrim()
    transform(prim, pos, rotation)
    return prim


def box(stage, path, pos, size, mat, rotation=None, collision=False):
    assert min(size) > 0
    prim = core.defineCube(stage, Sdf.Path(path), 1).GetPrim()
    transform(prim, pos, rotation, size)
    if collision:
        UsdPhysics.CollisionAPI.Apply(prim)
    return finish(stage, prim, mat)


def cylinder(stage, path, pos, radius, length, mat, axis="Z", collision=False):
    prim = core.defineCylinder(stage, Sdf.Path(path), radius, length, axis).GetPrim()
    transform(prim, pos)
    if collision:
        UsdPhysics.CollisionAPI.Apply(prim)
    return finish(stage, prim, mat)


def mesh(stage, path, points, faces, mat):
    prim = core.definePolyMesh(stage, Sdf.Path(path), Vt.IntArray([len(f) for f in faces]),
                              Vt.IntArray([i for f in faces for i in f]),
                              Vt.Vec3fArray([Gf.Vec3f(*p) for p in points])).GetPrim()
    UsdGeom.Mesh(prim).CreateDoubleSidedAttr(True)
    UsdGeom.Mesh(prim).CreateSubdivisionSchemeAttr("none")
    return finish(stage, prim, mat)


def beam(stage, path, a, b, width, depth, mat, collision=False):
    a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
    d = b-a
    return box(stage, path, (a+b)*.5, (width, depth, d.GetLength()), mat,
               Gf.Rotation(Gf.Vec3d(0, 0, 1), d.GetNormalized()), collision)


def tube(stage, path, a, b, radius, mat):
    a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
    d = b-a
    prim = core.defineCylinder(stage, Sdf.Path(path), radius, d.GetLength(), "Z").GetPrim()
    transform(prim, (a+b)*.5, Gf.Rotation(Gf.Vec3d(0, 0, 1), d.GetNormalized()))
    return finish(stage, prim, mat)


def install_adapter():
    # Keep the supplied source verbatim; redirect shared helpers through usdex.core.
    for name in ("material", "finish", "xform", "box", "cylinder", "mesh", "beam", "tube"):
        setattr(courtyard, name, globals()[name])
    courtyard.new_stage = lambda path: stage_at(courtyard.ROOT / path)


label = courtyard.label
rail = courtyard.railing
pin = courtyard.pin


def deck_rail(stage, path, a, b, height=1.1):
    """Rail authored on the initially vertical deck. Local -Y becomes world +Z."""
    a, b = Gf.Vec3d(*a), Gf.Vec3d(*b)
    count = max(1, math.ceil((b-a).GetLength()/1.5))
    for i in range(count+1):
        p = a + (b-a)*(i/count)
        beam(stage, path+f"/Post{i:02}", p, p+Gf.Vec3d(0, -height, 0), .05, .05, "silver")
    for j, h in enumerate((.52, height)):
        offset = Gf.Vec3d(0, -h, 0)
        beam(stage, path+f"/Rail{j}", a+offset, b+offset, .045, .045, "silver")
    beam(stage, path+"/Toe", a+Gf.Vec3d(0, -.08, 0), b+Gf.Vec3d(0, -.08, 0), .10, .10, "orange")
