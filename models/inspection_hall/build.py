"""Build the complete hall and a drive-only control, into a fresh directory."""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "source"))
import usdex.core as core
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdLux
from geometry import (courtyard, install_adapter, stage_at, box, cylinder, beam,
                      xform, label, rail, pin, deck_rail, transform)

SOURCE = Path(__file__).resolve().parent / "source"
P = json.loads((SOURCE / "design.json").read_text())


def compose(path, layers, description):
    stage = stage_at(path)
    stage.GetRootLayer().subLayerPaths = layers
    stage.GetRootLayer().documentation = description
    stage.GetRootLayer().customLayerData = {"preferredCamera": "/World/Cameras/InspectionWide"}
    stage.GetRootLayer().Save()
    return stage


def static_hall(output):
    stage = stage_at(output / "layers/02_static_hall.usda")
    roof_z = P["roof_hinge"][2]
    root = "/World/StaticHall"
    xform(stage, root).SetCustomDataByKey("role", "Fixed architecture; no pedestrian, load or structural simulation")
    # Repair kit namespaces using the supplied localization helper, preserving the site save.
    for side in (-1, 1):
        for i in range(8):
            p = stage.OverridePrim(f"/World/Site/Bollards/B{side+1}_{i}")
            p.GetReferences().AddReference("../assets/kit_v2.usda", "/World/Bollard")
    for side in (-1, 1):
        s = "West" if side < 0 else "East"
        x = side*12.6
        for j, y in enumerate((-8.65, -4.4, 0, 4.4, 8.7)):
            box(stage, root+f"/{s}/Column{j}", (x, y, (roof_z-.3)/2), (.23, .23, roof_z-.3), "graphite")
            box(stage, root+f"/{s}/Base{j}", (x, y, .12), (.75, .75, .24), "lightConcrete")
        # Side screen bays; the east rear bay is an open access doorway.
        for j in range(4):
            y = -6.5 + j*4.3
            box(stage, root+f"/{s}/LowWall{j}", (x, y, 1.0), (.12, 4.05, 1.85), "steel")
            box(stage, root+f"/{s}/Glass{j}", (x, y, 2.75), (.08, 4.05, 1.55), "glazing")
            if not (side > 0 and j == 3):
                box(stage, root+f"/{s}/UpperGlass{j}", (x, y, (3.7+roof_z-.4)/2), (.08, 4.05, roof_z-4.1), "glazing")
        box(stage, root+f"/{s}/Eave", (x, 0, roof_z-.25), (.30, 17.7, .18), "blue")
        # Fixed second-level gallery: 2.2 m wide, with a 1.8 m access throat at its south end.
        gx = side*11.3
        box(stage, root+f"/{s}/GalleryFloor", (gx, -.075, 3.86), (2.2, 17.75, .20), "teal")
        rail(stage, root+f"/{s}/InnerRail", (side*10.2, -8.94, 3.96), (side*10.2, 8.7, 3.96))
        for j in range(5):
            y = -8.2+j*4.2
            beam(stage, root+f"/{s}/GalleryBracket{j}", (x, y, 2.6), (side*10.3, y, 3.75), .12, .20, "steel")
        # Grounded bearing towers stand outside the moving side trusses.
        for j, (y, z) in enumerate(((-9, 3.8), (9, roof_z))):
            tx = side*16.7
            box(stage, root+f"/{s}/Tower{j}", (tx, y, z/2), (.6, 1.1, z), "concrete")
            box(stage, root+f"/{s}/Footing{j}", (tx, y, .15), (1.8, 2.0, .3), "lightConcrete")
            cylinder(stage, root+f"/{s}/Bearing{j}", (side*16.45, y, z), .43, .36, "graphite", "X")
    box(stage, root+"/North/Wall", (0, 9.25, (roof_z-.2)/2), (25.4, .24, roof_z-.2), "steel")
    for i in range(9):
        x = -11.8+i*2.95
        box(stage, root+f"/North/Window{i}", (x, 9.1, roof_z-2.2), (2.65, .04, 2.9), "glass")
        box(stage, root+f"/North/Rib{i}", (x, 9.02, (roof_z-.5)/2), (.10, .14, roof_z-.5), "blue")
    box(stage, root+"/North/Gallery", (0, 8.05, 3.86), (22.6, 1.6, .20), "teal")
    rail(stage, root+"/North/GalleryRail", (-10.2, 7.25, 3.96), (10.2, 7.25, 3.96))
    # A continuous 22-riser stair and landing enter the east gallery through its open screen bay.
    for i in range(22):
        y, z = -.5+i*.29, (i+1)*.18
        box(stage, root+f"/Stair/Tread{i:02}", (14.0, y, z-.04), (1.6, .30, .08), "silver")
    for x in (13.23, 14.77):
        beam(stage, root+f"/Stair/Stringer{int(x*100)}", (x, -.65, .05), (x, 5.7, 3.86), .12, .18, "graphite")
        rail(stage, root+f"/Stair/Handrail{int(x*100)}", (x, -.5, .18), (x, 5.59, 3.96))
    box(stage, root+"/Stair/Landing", (13.5, 6.6, 3.86), (2.8, 1.8, .20), "teal")
    rail(stage, root+"/Stair/OuterRail", (14.9, 5.7, 3.96), (14.9, 7.5, 3.96))
    rail(stage, root+"/Stair/EndRail", (12.5, 7.5, 3.96), (14.9, 7.5, 3.96))
    # Display equipment and vehicles have no rigid-body APIs.
    d = "/World/Display"
    xform(stage, d).SetCustomDataByKey("role", "Static inspection exhibit; not solver bodies or load tests")
    for i, x in enumerate((-5.0, 4.5)):
        p = xform(stage, d+f"/Vehicle{i}", (x, -3.8, .02))
        p.GetReferences().AddReference("../assets/proving_mule.usda", "/World")
        p.SetInstanceable(True)
        for side in (-1, 1):
            box(stage, d+f"/Bay{i}/Track{side+1}", (x+side*1.5, -3.8, .04), (.12, 7.0, .02), "teal")
        label(stage, d+f"/Bay{i}/ID", f"INSPECT 0{i+1}", (x-2.5, -7.6, .06), .5, "white", "XY")
        box(stage, d+f"/Console{i}/Stand", (x+2.4, 2.0, .6), (.7, .6, 1.2), "graphite")
        box(stage, d+f"/Console{i}/Screen", (x+2.4, 1.67, 1.35), (.8, .06, .55), "glass")
    label(stage, root+"/North/Title", "INSPECTION HALL", (-8.4, 9.0, roof_z-1.45), .85, "white")
    label(stage, root+"/East/LevelID", "LEVEL 02", (10.3, -8.98, 3.45), .24, "teal")
    # Visible stationary motor housing: the only drive lives on the rear roof hinge.
    cylinder(stage, root+"/M01/Stator", (18.0, 9.0, roof_z), .6, 1.6, "graphite", "X")
    for i in range(10):
        cylinder(stage, root+f"/M01/Fin{i}", (17.3+i*.15, 9, roof_z), .65, .04, "silver", "X")
    box(stage, root+"/M01/Support", (18.0, 9.0, (roof_z-.2)/2), (1.1, 1.4, roof_z-.2), "concrete")
    label(stage, root+"/M01/ID", "M01", (17.6, 8.28, roof_z-1.3), .4, "orange")
    # Same fixed wide camera in closed scene and replay. No render is performed.
    camera = Gf.Camera()
    camera.transform = Gf.Matrix4d().SetLookAt(Gf.Vec3d(55, -68, 43), Gf.Vec3d(0, -1, 9), Gf.Vec3d(0, 0, 1)).GetInverse()
    camera.focalLength, camera.horizontalAperture, camera.verticalAperture = 43, 36, 24
    camera.clippingRange = Gf.Range1f(.1, 1000)
    core.defineCamera(stage, Sdf.Path("/World/Cameras/InspectionWide"), camera)
    stage.GetRootLayer().documentation = "Fixed two-level galleries, staircase and display equipment; separate from the three rigid mechanism bodies."
    stage.GetRootLayer().Save()


def body(stage, name, pos, dims, com):
    path = "/World/Mechanism/" + name
    p = xform(stage, path, pos)
    rb = UsdPhysics.RigidBodyAPI.Apply(p)
    rb.CreateRigidBodyEnabledAttr(True)
    rb.CreateKinematicEnabledAttr(False)
    mass = P["masses_kg"][name]
    ma = UsdPhysics.MassAPI.Apply(p)
    ma.CreateMassAttr(mass)
    ma.CreateCenterOfMassAttr(Gf.Vec3f(*com))
    x, y, z = dims
    ma.CreateDiagonalInertiaAttr(Gf.Vec3f(mass*(y*y+z*z)/12, mass*(x*x+z*z)/12, mass*(x*x+y*y)/12))
    ma.CreatePrincipalAxesAttr(Gf.Quatf(1))
    p.AddAppliedSchema("PhysxRigidBodyAPI")
    for key, value, kind in (("solverPositionIterationCount", 64, Sdf.ValueTypeNames.Int),
                              ("solverVelocityIterationCount", 8, Sdf.ValueTypeNames.Int),
                              ("linearDamping", .03, Sdf.ValueTypeNames.Float),
                              ("angularDamping", .03, Sdf.ValueTypeNames.Float),
                              ("sleepThreshold", 0.0, Sdf.ValueTypeNames.Float)):
        p.CreateAttribute("physxRigidBody:"+key, kind, custom=False).Set(value)
    p.SetCustomDataByKey("role", "Motor input" if name == "RoofInput" else "Passive constrained body")
    return path


def hinge(stage, name, b0, b1, world_pos, limits=None):
    # SDK resolves the local anchor frames from the authored world-space pin location.
    frame = core.JointFrame(core.JointFrame.Space.World, Gf.Vec3d(*world_pos), Gf.Quatd(1))
    joint = core.definePhysicsRevoluteJoint(stage, Sdf.Path("/World/Joints/"+name),
                                           stage.GetPrimAtPath(b0) if b0 else Usd.Prim(),
                                           stage.GetPrimAtPath(b1), frame, Gf.Vec3f(1, 0, 0),
                                           limits[0] if limits else None, limits[1] if limits else None)
    joint.CreateCollisionEnabledAttr(False)
    joint.CreateJointEnabledAttr(True)
    if not b0:
        # SDK feedback: an invalid body0 left localPos0 at zero. For a world
        # joint USD explicitly requires the world-space anchor in localPos0.
        joint.CreateLocalPos0Attr(Gf.Vec3f(*world_pos))
        joint.CreateLocalRot0Attr(Gf.Quatf(1))
    return joint


def mechanism(output):
    stage = stage_at(output / "layers/03_mechanism.usda")
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr(P["gravity_m_s2"])
    scene.GetPrim().AddAppliedSchema("PhysxSceneAPI")
    for key, value, kind in (("solverType", "TGS", Sdf.ValueTypeNames.Token),
                              ("enableGPUDynamics", True, Sdf.ValueTypeNames.Bool),
                              ("timeStepsPerSecond", 120, Sdf.ValueTypeNames.UInt)):
        scene.GetPrim().CreateAttribute("physxScene:"+key, kind, custom=False).Set(value)
    roof_z = P["roof_hinge"][2]
    deck_z = P["deck_hinge"][2]
    dz = roof_z-deck_z
    length = P["crank_length_m"]
    front_pin = (0, -9-length, deck_z)
    rear_pin = (0, 9-length, roof_z)
    roof = body(stage, "RoofInput", P["roof_hinge"], (32, 18, dz+.1), (0, -9.4, -.35))
    deck = body(stage, "FrontLeafDeck", P["deck_hinge"], (32, .4, 3.5), (0, -.05, -1.75))
    tie = body(stage, "ConnectingYoke", front_pin, (32, 18, dz), (0, 9, dz/2))
    # A large blue roof and its upper south facade form one rigid input leaf.
    box(stage, roof+"/WeatherDeck", (0, -9, .30), (24.6, 18, .16), "steel", collision=True)
    box(stage, roof+"/UpperFacade", (0, -18, -(dz-.16)/2), (24.6, .18, dz-.10), "blue", collision=True)
    for i in range(8):
        x = -10.75+i*3.07
        box(stage, roof+f"/FacadeWindow{i}", (x, -18.11, -1.8), (2.85, .05, 1.7), "glass")
        for j in range(6):
            box(stage, roof+f"/Panels/P{i}_{j}", (x, -1.5-j*3, .41), (3.0, 2.94, .06), "silver" if i%3 else "lightConcrete")
    for j in range(7):
        y = -j*3
        box(stage, roof+f"/RoofRib{j}", (0, y, -.08), (24.4, .16, .38), "blue")
    label(stage, roof+"/Title", "COURTYARD / INSPECTION", (-10.4, -18.15, -.65), .68, "white")
    cylinder(stage, roof+"/TorqueShaft", (0, 0, 0), .22, 34.7, "orange", "X", True)
    for side in (-1, 1):
        x = side*P["side_arm_x_m"]
        box(stage, roof+f"/Crank{side+1}", (x, -length/2, 0), (.32, length, .45), "orange", collision=True)
        pin(stage, roof+f"/CrankPin{side+1}", (x, -length, 0), .22, .8)
        beam(stage, roof+f"/Outrigger{side+1}", (side*12.0, -2, 0), (x, 0, 0), .24, .24, "orange")
    cylinder(stage, roof+"/M01Disc", (17.1, 0, 0), .82, .22, "orange", "X")
    # The lower south facade becomes a teal inspection floor. Surface normal is local -Y.
    box(stage, deck+"/FloorSlab", (0, -.02, -1.75), (24.6, .28, 3.5), "teal", collision=True)
    for i in range(13):
        x = -12+i*2
        box(stage, deck+f"/Rib{i}", (x, .20, -1.75), (.12, .22, 3.45), "graphite")
        box(stage, deck+f"/GripStripe{i}", (x, -.163, -1.75), (.06, .006, 3.3), "silver")
    cylinder(stage, deck+"/HingeShaft", (0, 0, 0), .13, 32.8, "blue", "X")
    box(stage, deck+"/FreeEdgeBeam", (0, .09, -3.5), (24.6, .18, .22), "teal")
    for side in (-1, 1):
        box(stage, deck+f"/BellCrank{side+1}", (side*16, -length/2, 0), (.32, length, .45), "orange", collision=True)
        pin(stage, deck+f"/CouplerPin{side+1}", (side*16, -length, 0), .20, .8)
        deck_rail(stage, deck+f"/EdgeRail{side+1}", (side*12.2, -.16, -3.4), (side*12.2, -.16, -.03))
    deck_rail(stage, deck+"/FrontRail", (-12.2, -.16, -3.4), (12.2, -.16, -3.4))
    deck_rail(stage, deck+"/RearRail", (-10.05, -.16, -.03), (10.05, -.16, -.03))
    label(stage, deck+"/DeckID", "LEVEL 02 / INSPECTION DECK", (-10.5, -.168, -2.5), .57, "white")
    # Two side trusses plus a rear cross-shaft form one passive rigid connecting yoke.
    for side in (-1, 1):
        x = side*16
        beam(stage, tie+f"/CollisionArm{side+1}", (x, 0, 0), (x, 18, dz), .24, .24, "orange", True)
        for offset in (-.22, .22):
            beam(stage, tie+f"/Chord{side+1}_{'L' if offset < 0 else 'U'}", (x, 0, offset), (x, 18, dz+offset), .12, .12, "orange")
        for i in range(12):
            y0, y1 = i*1.5, (i+1)*1.5
            beam(stage, tie+f"/Web{side+1}_{i}", (x, y0, y0*dz/18+(-1)**i*.22),
                 (x, y1, y1*dz/18-(-1)**i*.22), .07, .09, "orange")
    cylinder(stage, tie+"/RearCrossShaft", (0, 18, dz), .16, 32.8, "orange", "X")
    driven = hinge(stage, "M01_Roof", None, roof, P["roof_hinge"], P["roof_limits_deg"])
    hinge(stage, "J02_Deck", None, deck, P["deck_hinge"], (-95, 5))
    hinge(stage, "J03_RoofToYoke", roof, tie, rear_pin)
    hinge(stage, "J04_DeckToYoke", deck, tie, front_pin)
    drive = UsdPhysics.DriveAPI.Apply(driven.GetPrim(), "angular")
    drive.CreateTypeAttr("force")
    drive.CreateTargetPositionAttr(P["target_angle_deg"])
    drive.CreateTargetVelocityAttr(0)
    drive.CreateStiffnessAttr(P["drive_stiffness"])
    drive.CreateDampingAttr(P["drive_damping"])
    drive.CreateMaxForceAttr(P["drive_max_force"])
    stage.GetRootLayer().documentation = "Three dynamic bodies, four revolute joints, one angular force drive. No authored motion samples."
    stage.GetRootLayer().Save()


def check_anchors(stage):
    """Reject disjointed initial hinges before the solver starts."""
    cache = UsdGeom.XformCache()
    for prim in stage.Traverse():
        if not prim.IsA(UsdPhysics.Joint):
            continue
        joint = UsdPhysics.Joint(prim)
        anchors = []
        for side in (0, 1):
            targets = getattr(joint, f"GetBody{side}Rel")().GetTargets()
            local = Gf.Vec3d(getattr(joint, f"GetLocalPos{side}Attr")().Get())
            anchors.append(cache.GetLocalToWorldTransform(stage.GetPrimAtPath(targets[0])).Transform(local) if targets else local)
        assert (anchors[1]-anchors[0]).GetLength() < 1e-5, str(prim.GetPath())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    install_adapter()
    courtyard.configure(output)
    courtyard.site()
    courtyard.localize_kit()
    courtyard.make_vehicle()
    static_hall(output)
    mechanism(output)
    layers = ["../layers/03_mechanism.usda", "../layers/02_static_hall.usda", "../layers/01_site.usda"]
    complete = compose(output / "saves/02_complete_closed.usda", layers,
                       "Complete authored hall. Closed configuration; no simulation poses. See source/design.json for parameters.")
    candidate = compose(output / "candidates/powered.usda", ["../saves/02_complete_closed.usda"],
                        "Powered mechanical candidate; geometry and static display retained together.")
    control = compose(output / "candidates/motor_disabled.usda", ["powered.usda"],
                      "Matched control. Only drive stiffness, damping and maxForce are overridden to zero.")
    prim = control.OverridePrim("/World/Joints/M01_Roof")
    for name in ("stiffness", "damping", "maxForce"):
        prim.CreateAttribute("drive:angular:physics:"+name, Sdf.ValueTypeNames.Float, custom=False).Set(0.0)
    control.GetRootLayer().Save()
    compose(output / "scene.usda", ["saves/02_complete_closed.usda"], "Complete inspection hall with InspectionWide camera.")
    check_anchors(complete)
    print(json.dumps({"scene": str(output / "scene.usda"),
                      "candidate": str(output / "candidates/powered.usda"),
                      "control": str(output / "candidates/motor_disabled.usda")}, indent=2))


if __name__ == "__main__":
    main()
