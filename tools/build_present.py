# Build the presentation root: models/wind_tunnel/scenes/present.usda (environment by reference) and
# models/wind_tunnel/scenes/present_payload.usda (identical, environment by payload, to prove ovrtx loads payloads).
#   python tools/build_present.py
#
# Adds what must never live in the environment payload: the Ahmed reference body, the lighting
# QC spheres, cameras, a BasisCurves ghost of the flow domain, and one RenderProduct per camera.
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meshlib as ml  # noqa: E402
from build_env import CFG as ENV  # noqa: E402

from project_paths import ROOT, MODEL

SCENES = {"reference": MODEL / "scenes" / "present.usda", "payload": MODEL / "scenes" / "present_payload.usda"}
ENV_ASSET = "../assets/test_section.usda"

# ---------------------------------------------------------------------------------------------
# Config (cm unless noted)
# ---------------------------------------------------------------------------------------------
# The props sit on the turntable centre, which build_env.py puts on the blueprint car's
# mid-wheelbase (Y 92.9, models/wind_tunnel/docs/fit-check.md), so the hero shots and the blueprint car share a centre.
CAR_X, CAR_Y = 0.0, ENV["turntable"]["cy"]

# Ahmed body, millimetres. Source: S. R. Ahmed, G. Ramm and G. Faltin, "Some Salient Features of
# the Time-Averaged Ground Vehicle Wake", SAE Technical Paper 840300 (1984), as restated by the
# ERCOFTAC knowledge base, test case AC1-05 (kbwiki.ercoftac.org/w/index.php/Description_AC1-05),
# checked 2026-10-26:
#   length 1044, width 389, height 288; nose rounding centred 100 mm from the front, top, bottom
#   and sides (radius 100); 50 mm above the ground plate on stilts of 30 mm diameter; every rear
#   end has the same slant part length, 222 mm.
# Not settled by those sources:
#   - whether 222 mm runs ALONG the slant or along the body axis. ERCOFTAC's split (forebody 182
#     + centre 640 + rear 222 = 1044) reads as axial; COMSOL's model of the same body reads it
#     along the slant (slant base height = 288 - 222 sin 25). Kept here ALONG the slant.
#   - the stilt positions. Neither source states them; they are placed for the presentation, the
#     lateral spacing chosen so the base plates land on the turntable clear of the belt frame.
AHMED = {
    "L": 1044.0, "W": 389.0, "H": 288.0, "nose_r": 100.0,
    "slant_deg": 25.0, "slant_len": 222.0,   # slant length, measured along the slanted surface
    "clearance": 50.0, "edge_r": 4.0,        # small radius on the long edges, for a highlight
    "stilt_d": 30.0,
    # From the nose: presentation placement, not sourced. The front pair sits at 300, not 202, so at
    # x4.3 its base plates land on bare turntable between the front wheel-drive belts and the
    # rear pair (checked by check_stilts below).
    "stilt_x": (300.0, 727.0),
    "stilt_y": 170.0,                        # +/- from the centreline: presentation placement
    "plate_d": 50.0, "plate_t": 6.0,         # base plates under the stilts
    "parting_w": 1.4, "parting_proud": 0.25,  # parting lines: nose block joint, slant insert joint
}
# The Ahmed body is a model-scale reference shape (1.044 m long). Shown at x4.3 it reads as a
# car-sized presentation prop (about 4.5 m long, 1.7 m wide, 1.45 m tall over the floor). The
# geometry is authored at true scale and the factor sits on the prop's transform.
AHMED_SCALE = 4.3

QC = {"radius": 25.0, "x": -250.0, "ys": (CAR_Y + 80.0, CAR_Y, CAR_Y - 80.0)}

CAMERAS = {
    # name: eye, target, focal (mm), horizontal aperture (mm), lens f-stop for depth of field
    # (0 = pinhole; focus is the eye-to-target distance)
    "Hero": ((-560.0, -680.0, 100.0), (0.0, 640.0, 250.0), 20.0, 36.0, 0.0),
    "Detail": ((-680.0, 500.0, 160.0), (-410.0, 900.0, 330.0), 30.0, 36.0, 2.8),
    # Beside the model, looking downstream at the collector bell mouth.
    "Wake": ((-470.0, 650.0, 170.0), (30.0, -1100.0, 280.0), 24.0, 36.0, 0.0),
}
# Explicit photographic exposure for our cameras (ovrtx reads the UsdGeomCamera exposure:*
# attributes; the bare `exposure` EV attribute has no effect). ovrtx's implicit default is
# f/5, 1/50 s, ISO 100. The CameraMAIN_00 copy takes only pose and lens from the blueprint (see MAIN).
EXPOSURE = {
    "Hero": {"fStop": 5.0, "time": 0.02, "iso": 100.0, "responsivity": 1.0},
    "Detail": {"fStop": 5.0, "time": 0.014, "iso": 100.0, "responsivity": 1.0},
    "Wake": {"fStop": 5.0, "time": 0.02, "iso": 100.0, "responsivity": 1.0},
}
# Pose and lens copied from the blueprint stage contract (layers/Cameras.usda, CameraMAIN_00). Its
# exposure (responsivity 1.103, auto-exposure API) and far clip (1e7) are NOT copied.
MAIN = {
    "translate": (-776.9374182833673, 653.5561542039375, 411.01190515011064),
    "rotateYXZ": (70.67873, 0.0, -125.65603),
    "focal": 18.147562, "h_ap": 20.955, "v_ap": 15.2908,
}
RENDER = {"resolution": (1920, 1080), "spp": 256}

# Animated camera /World/Cameras/Dolly: one slow move, rendered by tools/render_motion.py.
# It starts low on the wake side, behind the model's tail, then swings out to the left and cranes
# up while it dollies upstream, settling on a three-quarter view close to the Hero shot (nozzle and
# honeycomb beyond the model). Eye and target each follow one cubic Bezier, traversed with a
# cosine ease so the move starts and stops at rest. The camera looks at the target with world +Z
# up, so there is no roll. Samples are authored once per output frame, at time code
# frame * tcps / fps (the stage runs at 60 time codes per second; the move is cut at 24 fps).
DOLLY = {
    "fps": 24, "frames": 216,  # 9 s
    "eye": ((-60.0, -1000.0, 45.0), (-210.0, -900.0, 50.0), (-470.0, -720.0, 105.0), (-540.0, -560.0, 135.0)),
    "target": ((0.0, 40.0, 80.0), (0.0, 160.0, 110.0), (0.0, 450.0, 200.0), (0.0, 640.0, 250.0)),
    "focal": 20.0, "h_ap": 36.0,
    "exposure": {"fStop": 5.0, "time": 0.02, "iso": 100.0, "responsivity": 1.0},
    "min_clearance": 30.0,  # cm, from every gprim's world box (environment and props)
}


def bezier(ctrl, s):
    p0, p1, p2, p3 = (np.array(c, float) for c in ctrl)
    u = 1.0 - s
    return u ** 3 * p0 + 3 * u * u * s * p1 + 3 * u * s * s * p2 + s ** 3 * p3


def dolly_pose(frame):
    """Eye and target (cm) at an output frame, with ease in and out."""
    t = frame / (DOLLY["frames"] - 1)
    s = 0.5 - 0.5 * math.cos(math.pi * t)
    return bezier(DOLLY["eye"], s), bezier(DOLLY["target"], s)


# ---------------------------------------------------------------------------------------------
# Ahmed body mesh (true scale, cm). Nose faces +Y, into the oncoming flow.
# ---------------------------------------------------------------------------------------------
def slant_start():
    a = AHMED
    return a["L"] - a["slant_len"] * math.cos(math.radians(a["slant_deg"]))


def section(x):
    """Half width, bottom z and top z (mm) of the body's cross-section at x mm from the nose."""
    a = AHMED
    L, W, H, R, clr = a["L"], a["W"], a["H"], a["nose_r"], a["clearance"]
    d = 0.0
    if x < R:
        d = R - math.sqrt(max(R * R - (R - x) ** 2, 0.0))
    zt = clr + H - d
    if x > slant_start():
        zt = clr + H - (x - slant_start()) * math.tan(math.radians(a["slant_deg"]))
    return W / 2 - d, clr + d, zt


def parting_line(x):
    """A thin dark band around the body at x mm from the nose: a model's split line. Each edge
    follows the section at its own station, so the band hugs the nose curve and the slant."""
    a = AHMED
    w, o = a["parting_w"] / 2, a["parting_proud"]
    rings = []
    for xx, off in ((x - w, -0.6), (x - w, o), (x + w, o), (x + w, -0.6)):
        hw, zb, zt = section(xx)
        p = ml.rounded_rect(hw + off, zb - off, zt + off, a["edge_r"] + off, 6)
        rings.append(np.stack([p[:, 0], np.full(len(p), a["L"] / 2 - xx), p[:, 1]], 1))
    k = len(rings[0])
    pts = np.vstack(rings)
    faces = [[i * k + j, i * k + (j + 1) % k, ((i + 1) % 4) * k + (j + 1) % k, ((i + 1) % 4) * k + j]
             for i in range(4) for j in range(k)]
    if ml.signed_volume(pts, faces) < 0:
        faces = [f[::-1] for f in faces]
    return pts / 10.0, faces


def ahmed_mesh():
    a = AHMED
    L, R = a["L"], a["nose_r"]
    slant_x = slant_start()

    xs = [R - R * math.cos(al) for al in np.linspace(0, math.pi / 2, 17)]
    xs += [0.5 * (R + slant_x), slant_x, L]
    rings = []
    for x in xs:
        hw, zb, zt = section(x)
        p = ml.rounded_rect(hw, zb, zt, a["edge_r"], 6)
        rings.append(np.stack([p[:, 0], np.full(len(p), L / 2 - x), p[:, 1]], 1))
    pts, faces = ml.loft(rings, closed=True)
    k = len(rings[0])
    top = int(np.argmax(rings[0][:, 2] - np.abs(rings[0][:, 0]) * 1e-3))
    probe = 17 * k + top  # first body strip, top
    faces = ml.orient_outward(pts, faces, probe, (0, 0, 1))
    front = list(range(k))
    rear = list(range((len(rings) - 1) * k, len(rings) * k))
    if ml.newell(pts[front]) @ np.array([0, 1.0, 0]) < 0:
        front.reverse()
    if ml.newell(pts[rear]) @ np.array([0, -1.0, 0]) < 0:
        rear.reverse()
    faces += [front, rear]
    pts = pts / 10.0  # mm -> cm
    assert ml.signed_volume(pts, faces) > 0, "Ahmed body wound inward"
    return pts, faces


# ---------------------------------------------------------------------------------------------
def build(mode):
    import usdex.core as ux
    from pxr import Gf, Sdf, UsdGeom, UsdRender, Vt

    # Gf.Rotation() leaves its axis undefined, which intermittently authors NaN matrices.
    IDENTITY_ROT = Gf.Rotation(Gf.Vec3d(0, 0, 1), 0)

    path = SCENES[mode]
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = ux.createStage(str(path), "World", UsdGeom.Tokens.z, 0.01, "stagewright tools/build_present.py")
    stage.SetTimeCodesPerSecond(60)
    world = ux.defineXform(stage.GetDefaultPrim()).GetPrim()

    if mode == "reference":
        env = ux.defineReference(world, "WindTunnel", ENV_ASSET)
    else:
        env = ux.definePayload(world, "WindTunnel", ENV_ASSET)
    if not env:
        raise RuntimeError(f"could not {mode} {ENV_ASSET}")

    looks = ux.defineScope(world, "Looks").GetPrim()

    def mat(name, col, rough, metal=0.0, clearcoat=None, emissive=None):
        m = ux.definePreviewMaterial(looks, name, Gf.Vec3f(*col), roughness=rough, metallic=metal)
        if clearcoat is not None:
            sh = ux.computeEffectivePreviewSurfaceShader(m)
            sh.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(1.0)
            sh.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(clearcoat)
        if emissive is not None:
            ux.addEmissiveColorToPreviewMaterial(m, Gf.Vec3f(*emissive))
        return m

    m_body = mat("AhmedPaint", (0.80, 0.80, 0.79), 0.42)   # satin white model paint
    m_parting = mat("AhmedParting", (0.05, 0.05, 0.05), 0.6)
    m_stilt = mat("Stilt", (0.92, 0.92, 0.93), 0.07, metal=1.0)  # polished steel
    m_plate = mat("StiltPlate", (0.70, 0.70, 0.71), 0.25, metal=1.0)
    m_grey = mat("QcGrey18", (0.18, 0.18, 0.18), 0.95)
    m_chrome = mat("QcChrome", (0.95, 0.95, 0.95), 0.03, metal=1.0)
    m_paint = mat("QcPaint", (0.55, 0.03, 0.03), 0.25, clearcoat=0.03)
    m_ghost = mat("DomainGhost", (0.8, 0.8, 0.8), 0.6, emissive=(0.6, 0.6, 0.6))

    props = ux.defineXform(world, "Props").GetPrim()
    ahmed = ux.defineXform(props, "AhmedBody").GetPrim()
    ux.setLocalTransform(ahmed, Gf.Transform(Gf.Vec3d(CAR_X, CAR_Y, 0), IDENTITY_ROT,
                                             Gf.Vec3d(AHMED_SCALE, AHMED_SCALE, AHMED_SCALE)))
    mb = ml.MeshBuilder().add(*ahmed_mesh(), crease_deg=20.0)
    counts, idx, pts, nval, nidx = mb.arrays()
    body = ux.definePolyMesh(ahmed, "Body", Vt.IntArray.FromNumpy(counts), Vt.IntArray.FromNumpy(idx),
                             Vt.Vec3fArray.FromNumpy(pts),
                             normals=ux.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray.FromNumpy(nval),
                                                         Vt.IntArray.FromNumpy(nidx)))
    lo, hi = mb.extent()
    body.GetExtentAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*lo.tolist()), Gf.Vec3f(*hi.tolist())]))
    ux.bindMaterial(body.GetPrim(), m_body)
    a = AHMED
    pb = ml.MeshBuilder()
    for x in (a["nose_r"], slant_start()):  # nose block joint, interchangeable slant insert joint
        pb.add(*parting_line(x), crease_deg=40.0)
    counts, idx, pts, nval, nidx = pb.arrays()
    part = ux.definePolyMesh(ahmed, "PartingLines", Vt.IntArray.FromNumpy(counts), Vt.IntArray.FromNumpy(idx),
                             Vt.Vec3fArray.FromNumpy(pts),
                             normals=ux.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray.FromNumpy(nval),
                                                         Vt.IntArray.FromNumpy(nidx)))
    lo, hi = pb.extent()
    part.GetExtentAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*lo.tolist()), Gf.Vec3f(*hi.tolist())]))
    ux.bindMaterial(part.GetPrim(), m_parting)
    # Model units are cm at true scale under the x AHMED_SCALE transform. The plates sit on the
    # turntable top (world Z 0.10); each stilt runs from its plate 1 cm into the body.
    z0 = (ENV["turntable"]["top"] + 0.02) / AHMED_SCALE
    pt = a["plate_t"] / 10.0
    sh = a["clearance"] / 10.0 + 1.0 - z0 - pt
    k = 0
    for sx in a["stilt_x"]:
        for sy in (-a["stilt_y"], a["stilt_y"]):
            k += 1
            x, y = sy / 10.0, (a["L"] / 2 - sx) / 10.0
            cyl = ux.defineCylinder(ahmed, f"Stilt_{k}", a["stilt_d"] / 20.0, sh, "Z")
            ux.setLocalTransform(cyl.GetPrim(), Gf.Transform(Gf.Vec3d(x, y, z0 + pt + sh / 2),
                                                             IDENTITY_ROT, Gf.Vec3d(1, 1, 1)))
            ux.bindMaterial(cyl.GetPrim(), m_stilt)
            plate = ux.defineCylinder(ahmed, f"StiltPlate_{k}", a["plate_d"] / 20.0, pt, "Z")
            ux.setLocalTransform(plate.GetPrim(), Gf.Transform(Gf.Vec3d(x, y, z0 + pt / 2),
                                                               IDENTITY_ROT, Gf.Vec3d(1, 1, 1)))
            ux.bindMaterial(plate.GetPrim(), m_plate)

    qc = ux.defineXform(props, "QcSpheres").GetPrim()
    for (name, m), y in zip((("Grey18", m_grey), ("Chrome", m_chrome), ("Paint", m_paint)), QC["ys"]):
        s = ux.defineSphere(qc, name, QC["radius"])
        ux.setLocalTransform(s.GetPrim(), Gf.Transform(Gf.Vec3d(QC["x"], y, QC["radius"]), IDENTITY_ROT, Gf.Vec3d(1, 1, 1)))
        ux.bindMaterial(s.GetPrim(), m)

    # Flow-domain ghost: the 12 box edges as thin linear curves.
    d = ENV["domain"]
    corners = [(x, y, z) for x in d["x"] for y in d["y"] for z in d["z"]]
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count("1") == 1]
    cpts = [corners[i] for e in edges for i in e]
    guides = ux.defineScope(world, "Guides").GetPrim()
    ghost = ux.defineLinearBasisCurves(
        guides, "FlowDomain", Vt.IntArray([2] * len(edges)), Vt.Vec3fArray([Gf.Vec3f(*p) for p in cpts]),
        widths=ux.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.5])),
        displayColor=ux.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray([Gf.Vec3f(0.8, 0.8, 0.8)])))
    ux.bindMaterial(ghost.GetPrim(), m_ghost)

    cams = ux.defineScope(world, "Cameras").GetPrim()
    cam_paths = {}
    for name, (eye, target, focal, hap, fstop) in CAMERAS.items():
        view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1))
        focus = float(np.linalg.norm(np.subtract(target, eye)))
        gc = Gf.Camera(view.GetInverse(), Gf.Camera.Perspective, hap, hap * 9 / 16, 0, 0, focal,
                       Gf.Range1f(5, 100000), fStop=fstop, focusDistance=focus)
        cam = ux.defineCamera(cams, name, gc)
        ex = EXPOSURE[name]
        cam.CreateExposureFStopAttr(ex["fStop"])
        cam.CreateExposureTimeAttr(ex["time"])
        cam.CreateExposureIsoAttr(ex["iso"])
        cam.CreateExposureResponsivityAttr(ex["responsivity"])
        cam_paths[name] = cam.GetPath()
    main = UsdGeom.Camera.Define(stage, cams.GetPath().AppendChild("CameraMAIN_00"))
    main.CreateFocalLengthAttr(MAIN["focal"])
    main.CreateHorizontalApertureAttr(MAIN["h_ap"])
    main.CreateVerticalApertureAttr(MAIN["v_ap"])
    main.CreateClippingRangeAttr(Gf.Vec2f(1, 100000))
    main.AddTranslateOp().Set(Gf.Vec3d(*MAIN["translate"]))
    main.AddRotateYXZOp().Set(Gf.Vec3f(*MAIN["rotateYXZ"]))
    main.AddScaleOp().Set(Gf.Vec3f(1, 1, 1))
    cam_paths["Main"] = main.GetPath()

    dolly = UsdGeom.Camera.Define(stage, cams.GetPath().AppendChild("Dolly"))
    dolly.CreateFocalLengthAttr(DOLLY["focal"])
    dolly.CreateHorizontalApertureAttr(DOLLY["h_ap"])
    dolly.CreateVerticalApertureAttr(DOLLY["h_ap"] * 9 / 16)
    dolly.CreateClippingRangeAttr(Gf.Vec2f(5, 100000))
    ex = DOLLY["exposure"]
    dolly.CreateExposureFStopAttr(ex["fStop"])
    dolly.CreateExposureTimeAttr(ex["time"])
    dolly.CreateExposureIsoAttr(ex["iso"])
    dolly.CreateExposureResponsivityAttr(ex["responsivity"])
    pose = dolly.AddTransformOp()
    step = stage.GetTimeCodesPerSecond() / DOLLY["fps"]
    for f in range(DOLLY["frames"]):
        eye, target = dolly_pose(f)
        view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye.tolist()), Gf.Vec3d(*target.tolist()), Gf.Vec3d(0, 0, 1))
        pose.Set(view.GetInverse(), f * step)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode((DOLLY["frames"] - 1) * step)
    cam_paths["Dolly"] = dolly.GetPath()

    render = ux.defineScope(stage, Sdf.Path("/Render")).GetPrim()
    for name, cpath in cam_paths.items():
        prod = UsdRender.Product.Define(stage, render.GetPath().AppendChild(name))
        prod.CreateCameraRel().SetTargets([cpath])
        prod.CreateResolutionAttr(Gf.Vec2i(*RENDER["resolution"]))
        var = UsdRender.Var.Define(stage, prod.GetPath().AppendChild("Color"))
        var.CreateSourceNameAttr("LdrColor")
        prod.CreateOrderedVarsRel().SetTargets([var.GetPath()])
        p = prod.GetPrim()
        p.CreateAttribute("omni:rtx:rendermode", Sdf.ValueTypeNames.Token).Set("PathTracing")
        p.CreateAttribute("omni:rtx:pt:samplesPerPixel", Sdf.ValueTypeNames.UInt).Set(RENDER["spp"])
        p.CreateAttribute("omni:rtx:pt:denoising:enabled", Sdf.ValueTypeNames.Bool).Set(True)

    ux.saveStage(stage, comment=f"Presentation root ({mode} to the environment). Generated; do not hand-edit.")
    if re.search(r"\bnan\b", path.read_text(encoding="utf-8"), re.IGNORECASE):
        raise RuntimeError(f"NaN authored in {path}")
    print("wrote", path)


def check_dolly(path):
    """Refuse a dolly path that comes within min_clearance of any gprim's world box, environment or
    props. A box is conservative: it also keeps the camera out of the nozzle and collector ducts."""
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boxes = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Gprim) or str(prim.GetPath()).startswith(("/World/Guides", "/World/Cameras")):
            continue
        r = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if not r.IsEmpty():
            boxes.append((str(prim.GetPath()), np.array(r.GetMin()), np.array(r.GetMax())))
    cam = UsdGeom.Camera(stage.GetPrimAtPath("/World/Cameras/Dolly"))
    xf = UsdGeom.XformCache()
    worst = (1e9, None, None)
    step = stage.GetTimeCodesPerSecond() / DOLLY["fps"]
    for f in range(DOLLY["frames"]):
        xf.SetTime(Usd.TimeCode(f * step))
        p = np.array(xf.GetLocalToWorldTransform(cam.GetPrim()).ExtractTranslation())
        for name, lo, hi in boxes:
            d = float(np.linalg.norm(np.maximum(np.maximum(lo - p, 0), p - hi)))
            if d < worst[0]:
                worst = (d, name, f)
    print(f"dolly: {len(boxes)} gprim boxes, closest {worst[0]:.1f} cm to {worst[1]} at frame {worst[2]}")
    if worst[0] < DOLLY["min_clearance"]:
        raise RuntimeError(f"dolly path within {DOLLY['min_clearance']} cm of {worst[1]}")


def check_stilts(path, margin=2.0):
    """Refuse Ahmed stilt base plates that touch a belt unit's frame or slot (they must stand on bare
    turntable), or that leave the turntable."""
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    belts = []
    for name in ("RollingRoadPlates", "RollingRoadSlot", "WheelBeltFrames", "WheelBeltSlots"):
        prim = next((p for p in stage.Traverse() if p.GetName() == name), None)
        if prim is None:
            raise RuntimeError(f"check_stilts: {name} not found")
        pts = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), float)[:, :2]
        if name.startswith("Wheel"):  # four units: split by side and by axle
            for sx in (-1, 1):
                for sy in (-1, 1):
                    q = pts[(np.sign(pts[:, 0]) == sx) & (np.sign(pts[:, 1] - CAR_Y) == sy)]
                    belts.append((f"{name}[{sx:+d},{sy:+d}]", q.min(0), q.max(0)))
        else:
            belts.append((name, pts.min(0), pts.max(0)))
    tt = ENV["turntable"]
    worst = (1e9, None, None)
    for prim in stage.Traverse():
        if not prim.GetName().startswith("StiltPlate_"):
            continue
        r = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        lo, hi = np.array(r.GetMin())[:2], np.array(r.GetMax())[:2]
        corners = np.array([[x, y] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])])
        if np.hypot(corners[:, 0] - tt["cx"], corners[:, 1] - tt["cy"]).max() > tt["r"] - tt["ring_w"]:
            raise RuntimeError(f"{prim.GetName()} leaves the turntable disc")
        for name, blo, bhi in belts:
            d = float(np.linalg.norm(np.maximum(np.maximum(blo - hi, lo - bhi), 0)))
            if d < worst[0]:
                worst = (d, prim.GetName(), name)
    print(f"stilts: closest plate {worst[1]} is {worst[0]:.1f} cm from {worst[2]}")
    if worst[0] < margin:
        raise RuntimeError(f"{worst[1]} within {margin} cm of {worst[2]}")


if __name__ == "__main__":
    for mode in SCENES:
        build(mode)
    check_dolly(SCENES["reference"])
    check_stilts(SCENES["reference"])
