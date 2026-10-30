"""Author a four-bar readiness rig, not the grand construction experiment.

One driven crank raises a bridge through an undriven follower and four revolute
constraints. Zero gravity isolates drive causality; no-drive is a counterfactual.
"""
import argparse
import math
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdRender, UsdShade


def make(destination, driven=True):
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(destination))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    UsdGeom.Scope.Define(stage, "/World/Joints")
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1)
    stage.SetTimeCodesPerSecond(120)
    scene = UsdPhysics.Scene.Define(stage, "/World/Physics")
    scene.CreateGravityMagnitudeAttr(0)
    # Codeless attributes are registered by the worker before population.
    scene.GetPrim().SetMetadata("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["PhysxSceneAPI"]))
    for name, kind, value in (("enableGPUDynamics", Sdf.ValueTypeNames.Bool, True),
                              ("broadphaseType", Sdf.ValueTypeNames.Token, "GPU"),
                              ("solverType", Sdf.ValueTypeNames.Token, "TGS"),
                              ("minPositionIterationCount", Sdf.ValueTypeNames.UInt, 32)):
        scene.GetPrim().CreateAttribute(f"physxScene:{name}", kind).Set(value)

    def material(name, color):
        mat = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        shader = UsdShade.Shader.Define(stage, f"{mat.GetPath()}/Surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.35)
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return mat

    steel = material("Steel", (0.22, 0.28, 0.34))
    orange = material("Drive", (0.9, 0.22, 0.03))
    blue = material("Follower", (0.05, 0.35, 0.65))

    def box(path, dimensions, position, mat):
        shape = UsdGeom.Cube.Define(stage, path)
        shape.CreateSizeAttr(1)
        shape.AddTranslateOp().Set(Gf.Vec3d(*position))
        shape.AddScaleOp().Set(Gf.Vec3f(*dimensions))
        UsdShade.MaterialBindingAPI.Apply(shape.GetPrim()).Bind(mat)
        return shape

    angle = math.radians(30)
    end = (2 * math.cos(angle), 0, 1 + 2 * math.sin(angle))
    bodies = {}
    for name, origin, rotation, size, mat in (
        ("Crank", (0, 0, 1), -30, (2, 0.24, 0.24), orange),
        ("Follower", (6, 0, 1), -30, (2, 0.24, 0.24), blue),
        ("Bridge", end, 0, (6, 1.6, 0.2), steel),
    ):
        body = UsdGeom.Xform.Define(stage, f"/World/{name}")
        body.AddTranslateOp().Set(Gf.Vec3d(*origin))
        body.AddOrientOp().Set(Gf.Quatf(Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation).GetQuat()))
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        UsdPhysics.MassAPI.Apply(body.GetPrim()).CreateMassAttr(1)
        shape = box(f"{body.GetPath()}/Shape", size, (size[0] / 2, 0, 0), mat)
        UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
        bodies[name] = body.GetPath()
    box("/World/Floor", (15, 9, 0.15), (4, 0, -0.1), steel)
    for i, x in enumerate((0, 6)):
        box(f"/World/Pedestal{i}", (0.4, 0.6, 1), (x, 0, 0.5), steel)

    def hinge(name, first, second, pos0, pos1, rot0=0, rot1=0):
        joint = UsdPhysics.RevoluteJoint.Define(stage, f"/World/Joints/{name}")
        joint.CreateAxisAttr("Y")
        if first:
            joint.CreateBody0Rel().SetTargets([bodies[first]])
        joint.CreateBody1Rel().SetTargets([bodies[second]])
        joint.CreateLocalPos0Attr(Gf.Vec3f(*pos0))
        joint.CreateLocalPos1Attr(Gf.Vec3f(*pos1))
        for setter, rotation in ((joint.CreateLocalRot0Attr, rot0), (joint.CreateLocalRot1Attr, rot1)):
            setter(Gf.Quatf(Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation).GetQuat()))
        return joint

    actuator = hinge("Drive", None, "Crank", (0, 0, 1), (0, 0, 0), rot1=30)
    hinge("GroundFollower", None, "Follower", (6, 0, 1), (0, 0, 0), rot1=30)
    hinge("CrankBridge", "Crank", "Bridge", (2, 0, 0), (0, 0, 0), rot0=30)
    hinge("BridgeFollower", "Bridge", "Follower", (6, 0, 0), (2, 0, 0), rot1=30)
    if driven:
        drive = UsdPhysics.DriveAPI.Apply(actuator.GetPrim(), "angular")
        drive.CreateTypeAttr("force")
        drive.CreateTargetPositionAttr(-40)
        drive.CreateStiffnessAttr(120)
        drive.CreateDampingAttr(35)
        drive.CreateMaxForceAttr(500)

    dome = UsdLux.DomeLight.Define(stage, "/World/Sky")
    dome.CreateIntensityAttr(350)
    light = UsdLux.RectLight.Define(stage, "/World/Key")
    light.CreateWidthAttr(6)
    light.CreateHeightAttr(6)
    light.CreateIntensityAttr(12000)
    light.AddTranslateOp().Set(Gf.Vec3d(4, 0, 10))
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera.CreateFocalLengthAttr(35)
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.01, 1000))
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(
        Gf.Vec3d(12, -15, 8), Gf.Vec3d(4, 0, 2), Gf.Vec3d(0, 0, 1)).GetInverse())
    product = UsdRender.Product.Define(stage, "/Render/Mechanism")
    product.CreateCameraRel().SetTargets([camera.GetPath()])
    product.CreateResolutionAttr(Gf.Vec2i(960, 540))
    color = UsdRender.Var.Define(stage, "/Render/Mechanism/Color")
    color.CreateSourceNameAttr("LdrColor")
    product.CreateOrderedVarsRel().SetTargets([color.GetPath()])
    product.GetPrim().CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token).Set("PathTracing")
    stage.GetRootLayer().Save()
    print(f"Readiness rig -> {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--no-drive", action="store_true")
    args = parser.parse_args()
    make(args.destination, not args.no_drive)
