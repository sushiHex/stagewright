# Fit check: does the open-jet environment drop into the blueprint stage cleanly?
#   python tools/fit_check.py          run every check and write docs/fit-check.md
#   python tools/fit_check.py --strict also fail on any check that could not run
#
# Opens scenes/blueprint_override.usda (which sublayers the blueprint's Main.usda and replaces the
# /World/WindTunnel payload), then measures everything from the composed stage and the blueprint's
# own layer files. Nothing here trusts a number written in CLAUDE.md or tools/build_env.py: those
# are only used as the "expected" column, and every source value is cited by file:line.
#
# Exit status is 1 if any check FAILS (or, with --strict, is NOT CHECKED). Checks that could not run,
# such as the car checks without the CarHero LFS content, are reported as NOT CHECKED.
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OVERRIDE = ROOT / "scenes" / "blueprint_override.usda"
ASSET = ROOT / "assets" / "test_section.usda"
REPORT = ROOT / "docs" / "fit-check.md"
BP = ROOT / "external" / "blueprint"
STAGES = BP / "source" / "specializations" / "auto-aero" / "stages"
OLD_ENV_DIR = STAGES / "layers" / "WindTunnel"
# The private render of the blueprint stage through the override (shows their car, never published).
# build/private/blueprint_root.usda is a local, untracked root that sublayers the override and adds a
# RenderProduct "BlueprintMain" on their CameraMAIN_00; it is rendered with
#   python tools/render.py --scene build/private/blueprint_root.usda --products BlueprintMain --out build/private
PRIVATE_RENDER = ROOT / "build" / "private" / "blueprint_root_blueprintmain.png"

# The numbers CLAUDE.md records (the "expected" column only).
CLAUDE_DOMAIN = {"x": (-144.0, 144.0), "y": (-650.0, 430.0), "z": (-4.0, 248.0)}
CLAUDE_CAR = {"translate": (0.0, 250.0, 0.0), "rotateXYZ": (90.0, 0.0, 0.0)}
CLAUDE_CAM = {"translate": (-776.9, 653.6, 411.0), "rotateYXZ": (70.68, 0.0, -125.66),
              "focalLength": 18.15, "horizontalAperture": 20.955, "verticalAperture": 15.29}

# Every camera the blueprint stage defines (layers/Cameras.usda and its per-camera payloads). A camera
# payload that fails to load would silently drop out of every camera check, so the set is asserted.
EXPECTED_CAMERAS = ("Orbit_Camera", "Camera_ANIM1", "Camera_ANIM2", "Camera_ANIM3", "Camera_ANIM4",
                    "Camera_ANIM5", "FullOrbit_Camera", "CameraMAIN_00")

FLOOR_ALLOWANCE_Z = 0.5  # floor inserts (turntable, belt) may overlap the domain only below this
LFS_MAGIC = b"version https://git-lfs.github.com/spec/v1"

results = []   # (check, status, detail)
md = []        # report body
CAMERA_OPENING = []  # (camera, part, time, position) samples inside a duct opening
NOZZLE_LIP_Y = None


def record(check, status, detail=""):
    results.append((check, status, detail))
    print(f"[{status}] {check}" + (f": {detail}" if detail else ""))


def rel(p):
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def fmt(v, nd=1):
    return "(" + ", ".join(f"{x:.{nd}f}" for x in v) + ")"


def find_line(path, anchors):
    """1-based line of the last anchor, each anchor searched after the previous one."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    for a in anchors:
        rx = re.compile(a)
        while i < len(lines) and not rx.search(lines[i]):
            i += 1
        if i == len(lines):
            return None
        i += 1
    return i


def cite(path, anchors):
    n = find_line(path, anchors)
    return f"`{rel(path)}:{n}`" if n else f"`{rel(path)}` (line not found)"


def is_lfs_pointer(path):
    try:
        with open(path, "rb") as f:
            return f.read(len(LFS_MAGIC)) == LFS_MAGIC
    except OSError:
        return False


def world_points(prim, xf):
    from pxr import UsdGeom
    pts = UsdGeom.PointBased(prim).GetPointsAttr().Get()
    if pts is None or len(pts) == 0:
        return None
    m = np.array(xf.GetLocalToWorldTransform(prim))
    a = np.asarray(pts, dtype=np.float64)
    return a @ m[:3, :3] + m[3, :3]


def renderable(prim):
    from pxr import UsdGeom
    img = UsdGeom.Imageable(prim)
    return img.ComputeVisibility() != UsdGeom.Tokens.invisible and \
        img.ComputePurpose() in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)


def aabb_gap(lo_a, hi_a, lo_b, hi_b):
    """Per-axis separation between two boxes (0 where they overlap on that axis) and its norm."""
    g = np.maximum(0.0, np.maximum(lo_b - hi_a, lo_a - hi_b))
    return g, float(np.linalg.norm(g))


def rect_dist(x, z, xr, zr):
    """Distance from points (x, z) to the rectangle xr x zr; 0 inside."""
    dx = np.maximum(0.0, np.maximum(xr[0] - x, x - xr[1]))
    dz = np.maximum(0.0, np.maximum(zr[0] - z, z - zr[1]))
    return np.hypot(dx, dz)


# -------------------------------------------------------------------------------------------------
# 1. Override layer and composition
# -------------------------------------------------------------------------------------------------
def check_composition():
    from pxr import Sdf, Usd, UsdGeom, UsdUtils

    md.append("## 1. Override layer and composition\n")
    lay = Sdf.Layer.FindOrOpen(str(OVERRIDE))
    meta_ok = (lay.pseudoRoot.GetInfo("upAxis") == "Z" and lay.pseudoRoot.GetInfo("metersPerUnit") == 0.01
               and lay.timeCodesPerSecond == 60)
    md.append(f"- Root layer `{rel(OVERRIDE)}`: upAxis `{lay.pseudoRoot.GetInfo('upAxis')}`, metersPerUnit "
              f"`{lay.pseudoRoot.GetInfo('metersPerUnit')}`, timeCodesPerSecond `{lay.timeCodesPerSecond}`, "
              f"sublayers `{list(lay.subLayerPaths)}`.")
    record("Override root layer metadata (Z-up, mpu 0.01, tcps 60)", "PASS" if meta_ok else "FAIL")

    asset = Sdf.Layer.FindOrOpen(str(ASSET))
    a_ok = (asset.pseudoRoot.GetInfo("upAxis") == "Z" and asset.pseudoRoot.GetInfo("metersPerUnit") == 0.01)
    md.append(f"- Environment asset `{rel(ASSET)}`: upAxis `{asset.pseudoRoot.GetInfo('upAxis')}`, metersPerUnit "
              f"`{asset.pseudoRoot.GetInfo('metersPerUnit')}`, timeCodesPerSecond `{asset.timeCodesPerSecond}`. "
              "USD does not rescale a payload for a units mismatch, so these must match the blueprint.")
    record("Environment asset units match the blueprint (Z-up, mpu 0.01)", "PASS" if a_ok else "FAIL")

    # The authored opinion on our layer must be an explicit list-op, not prepend/append/add.
    spec = lay.GetPrimAtPath("/World/WindTunnel")
    plo = spec.GetInfo("payload") if spec else None
    explicit = bool(plo) and plo.isExplicit and not (plo.prependedItems or plo.appendedItems or plo.addedItems
                                                     or plo.deletedItems)
    md.append(f"- Our opinion on `/World/WindTunnel`: `{plo}` (explicit: {explicit}).")
    record("Override payload is an explicit list-op", "PASS" if explicit else "FAIL", str(plo))

    diag = UsdUtils.CoalescingDiagnosticDelegate()
    stage = Usd.Stage.Open(str(OVERRIDE), Usd.Stage.LoadNone)
    open_diags = diag.TakeUncoalescedDiagnostics()
    wt = stage.GetPrimAtPath("/World/WindTunnel")

    md.append("\nLayer stack opinions on `/World/WindTunnel` (strongest first):\n")
    for s in wt.GetPrimStack():
        if s.HasInfo("payload"):
            md.append(f"- `{rel(s.layer.realPath)}`: `{s.GetInfo('payload')}`")
    composed = wt.GetMetadata("payload")
    final = composed.ApplyOperations([]) if composed else []
    only_ours = (len(final) == 1 and Path(final[0].assetPath).name == ASSET.name
                 and str(final[0].primPath) == "/Environment")
    md.append(f"\nComposed payload list-op: `{composed}`; resolved list after applying operations: "
              f"`{[ (p.assetPath, str(p.primPath)) for p in final ]}`.")
    record("Composed payload list on /World/WindTunnel is ONLY our asset", "PASS" if only_ours else "FAIL",
           f"{len(final)} item(s)")

    stage.Load("/World/WindTunnel")
    from pxr import Pcp
    arcs = [a for a in Usd.PrimCompositionQuery(wt).GetCompositionArcs()
            if a.GetArcType() == Pcp.ArcTypePayload]
    arc_desc = [(Path(a.GetTargetNode().layerStack.identifier.rootLayer.realPath).name, str(a.GetTargetNode().path))
                for a in arcs]
    used = [Path(l.realPath).name for l in stage.GetUsedLayers() if l.realPath]
    old_used = [u for u in used if u.startswith("windTunnelEnv")]
    arcs_ok = arc_desc == [(ASSET.name, "/Environment")] and not old_used
    md.append(f"\nAfter loading `/World/WindTunnel`, its payload arcs are `{arc_desc}`; layers named "
              f"`windTunnelEnv*` among the stage's used layers: `{old_used}`.")
    record("Loaded payload arcs: one arc to test_section.usda:/Environment, old env layer unused",
           "PASS" if arcs_ok else "FAIL", str(arc_desc))

    xf = UsdGeom.XformCache()
    m = xf.GetLocalToWorldTransform(wt)
    ident = np.allclose(np.array(m), np.eye(4), atol=1e-9)
    md.append(f"\n`/World/WindTunnel` local-to-world: `{np.array(m).round(6).tolist()}` (identity: {ident}).")
    record("/World/WindTunnel local-to-world is identity", "PASS" if ident else "FAIL")

    # Now load everything, so the car, cameras and data payloads all report their problems.
    stage.Load()
    load_diags = diag.TakeUncoalescedDiagnostics()
    errs = stage.GetCompositionErrors()
    classify_problems(stage, open_diags + load_diags, errs)
    return stage


def classify(path_text):
    """Return a category for an unresolved or suspicious asset path."""
    t = path_text.replace("\\", "/")
    if re.match(r"^[a-z]+://", t) or "amazonaws.com" in t and not os.path.exists(t):
        return "remote content"
    if os.path.exists(t):
        return "git-lfs pointer (file present, content not fetched)" if is_lfs_pointer(t) else "present"
    if "/data/" in t:
        return "blueprint data not in the git repo (downloaded separately)"
    return "missing file"


def classify_problems(stage, diags, errs):
    from pxr import Sdf, UsdGeom

    md.append("\n### Composition errors and missing assets (stage fully loaded)\n")
    if not errs and not diags:
        md.append("- No composition errors and no diagnostics.")
    for e in errs:
        text = str(e)
        m = re.search(r"@([^@]+)@", text)
        cat = classify(m.group(1)) if m else "other"
        md.append(f"- Composition error, **{cat}**: `{text[:400]}`")
    seen = {str(e)[:120] for e in errs}
    for d in diags:
        if any(d.commentary[:60] in s or s[:60] in d.commentary for s in seen):
            continue
        m = re.search(r"@([^@]+)@", d.commentary)
        cat = classify(m.group(1)) if m else "other"
        md.append(f"- Diagnostic `{d.diagnosticCodeString}`, **{cat}**: `{d.commentary[:300]}`")
    ours = [e for e in errs if ASSET.name in str(e) or "/World/WindTunnel" in str(e)]
    record("No composition errors from our environment", "PASS" if not ours else "FAIL",
           f"{len(errs)} error(s) on the stage, {len(ours)} from the environment")

    # Asset-valued attributes (textures, MDL): classify every one that does not resolve to real content.
    counts = Counter()
    examples = {}
    for prim in stage.Traverse():
        owner = "/".join(str(prim.GetPath()).split("/")[:3])
        for attr in prim.GetAttributes():
            tn = attr.GetTypeName()
            if tn not in (Sdf.ValueTypeNames.Asset, Sdf.ValueTypeNames.AssetArray):
                continue
            v = attr.Get()
            vals = [v] if tn == Sdf.ValueTypeNames.Asset else list(v or [])
            for a in vals:
                if not a or not a.path:
                    continue
                rp = a.resolvedPath
                if rp:
                    cat = "git-lfs pointer (file present, content not fetched)" if is_lfs_pointer(rp) else None
                elif re.match(r"^[a-z]+://", a.path):
                    cat = "remote content"
                elif a.path.endswith((".mdl", ".xac")) and not a.path.startswith((".", "/")):
                    cat = "MDL or shader search path (resolved by the renderer, not by Ar)"
                else:
                    cat = "unresolved"
                if cat:
                    counts[(owner, cat)] += 1
                    examples.setdefault((owner, cat), f"{prim.GetPath()}.{attr.GetName()} = @{a.path}@")
    md.append("\nAsset-valued attributes that do not resolve to real content, by owner:\n")
    if not counts:
        md.append("- None.")
    md.append("| Owner | Category | Count | Example |\n|---|---|---|---|")
    for (owner, cat), n in sorted(counts.items()):
        md.append(f"| `{owner}` | {cat} | {n} | `{examples[(owner, cat)][:140]}` |")
    ours = sum(n for (o, c), n in counts.items() if o == "/World/WindTunnel")
    record("Environment asset attributes all resolve", "PASS" if ours == 0 else "FAIL",
           f"{ours} unresolved in /World/WindTunnel; {sum(counts.values())} on the whole stage")


# -------------------------------------------------------------------------------------------------
# 2. CFD domain recomputed from source
# -------------------------------------------------------------------------------------------------
def rot_xyz(deg):
    from pxr import Gf
    x, y, z = deg
    # USD rotateXYZ: rotate about X first, then Y, then Z (row-vector convention: Rx * Ry * Rz).
    return (Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 0), x))
            * Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), y))
            * Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), z)))


def check_domain(stage):
    from pxr import Gf, Sdf, UsdGeom

    md.append("\n## 2. CFD domain, recomputed from the blueprint source\n")
    base = STAGES / "Base.usda"
    bl = Sdf.Layer.FindOrOpen(str(base))
    cae = bl.GetPrimAtPath("/World/CAE")
    t = Gf.Vec3d(cae.attributes["xformOp:translate"].default)
    r = Gf.Vec3d(cae.attributes["xformOp:rotateXYZ"].default)
    s = Gf.Vec3d(cae.attributes["xformOp:scale"].default)
    order = list(cae.attributes["xformOpOrder"].default)
    m_src = Gf.Matrix4d().SetScale(s) * rot_xyz(r) * Gf.Matrix4d().SetTranslate(t)
    cae_anchor = [r'def Xform "CAE"']
    md.append(f"- `/World/CAE` in Base.usda: translate {fmt(t)} ({cite(base, cae_anchor + ['xformOp:translate'])}), "
              f"rotateXYZ {fmt(r)} ({cite(base, cae_anchor + ['xformOp:rotateXYZ'])}), scale {fmt(s)} "
              f"({cite(base, cae_anchor + ['xformOp:scale'])}), xformOpOrder {order}.")
    m_comp = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath("/World/CAE"))
    same = np.allclose(np.array(m_src), np.array(m_comp), atol=1e-6)
    md.append(f"- The composed `/World/CAE` local-to-world equals the matrix rebuilt from those source values: {same} "
              "(so no stronger layer overrides it).")
    record("/World/CAE composed transform matches Base.usda source values", "PASS" if same else "FAIL")

    sel = stage.GetPrimAtPath("/World/Domain").GetVariantSets().GetVariantSelection("Refinement")
    md.append(f"- `/World/Domain` Refinement selection on the composed stage: `{sel}` "
              f"({cite(base, [r'def OmniSciDataset \"Domain\"', 'string Refinement'])}).")
    md.append("\n| Refinement | origin | spacing | minExtent | maxExtent | local box (m) | world box (cm) | source |"
              "\n|---|---|---|---|---|---|---|---|")
    boxes = {}
    for var in ("Approx_2M", "Approx_14M", "Approx_108M"):
        vs = bl.GetPrimAtPath(f"/World/Domain{{Refinement={var}}}")
        if not vs:
            continue
        a = {k: vs.attributes[f"omni:vtk:{k}"].default for k in ("origin", "spacing", "minExtent", "maxExtent")}
        o, sp = np.array(a["origin"], float), np.array(a["spacing"], float)
        lo = o + np.array(a["minExtent"], float) * sp
        hi = o + np.array(a["maxExtent"], float) * sp
        corners = [Gf.Vec3d(*(lo[i] if (k >> i) & 1 == 0 else hi[i] for i in range(3))) for k in range(8)]
        w = np.array([m_src.Transform(c) for c in corners])
        boxes[var] = (w.min(0), w.max(0))
        md.append(f"| {var} | {tuple(a['origin'])} | {tuple(round(x, 4) for x in a['spacing'])} | "
                  f"{tuple(a['minExtent'])} | {tuple(a['maxExtent'])} | {fmt(lo, 3)}..{fmt(hi, 3)} | "
                  f"{fmt(w.min(0))}..{fmt(w.max(0))} | "
                  f"{cite(base, [r'def OmniSciDataset \"Domain\"', f'\"{var}\"', 'omni:vtk:minExtent'])} |")
    lo_w, hi_w = boxes[sel]
    agree = all(np.allclose(b[0], lo_w, atol=0.05) and np.allclose(b[1], hi_w, atol=0.05) for b in boxes.values())
    md.append(f"\nAll refinement variants describe the same box: {agree}.")

    # The ROI curve under /World/CAE should trace the same box (it is what AppState's roi rel points at).
    bb = stage.GetPrimAtPath("/World/CAE/BoundingBox_Domain")
    bcae = STAGES / "BaseCAE.usda"
    if bb:
        pts = np.asarray(bb.GetAttribute("points").Get(), float)
        mm = np.array(UsdGeom.XformCache().GetLocalToWorldTransform(bb))
        wp = pts @ mm[:3, :3] + mm[3, :3]
        roi_same = np.allclose(wp.min(0), lo_w, atol=0.05) and np.allclose(wp.max(0), hi_w, atol=0.05)
        md.append(f"`/World/CAE/BoundingBox_Domain` ({cite(bcae, [r'def BasisCurves \"BoundingBox_Domain\"'])}), the "
                  f"prim `AppState`'s roi rel targets ({cite(bcae, ['omni:rtwt:app_state:roi'])}), spans "
                  f"{fmt(wp.min(0))}..{fmt(wp.max(0))} in world space, the same box: {roi_same}.")
    claude_lo = np.array([CLAUDE_DOMAIN[k][0] for k in "xyz"])
    claude_hi = np.array([CLAUDE_DOMAIN[k][1] for k in "xyz"])
    ok = np.allclose(lo_w, claude_lo, atol=0.05) and np.allclose(hi_w, claude_hi, atol=0.05)
    md.append(f"\nDomain in world space (cm): **X {lo_w[0]:.1f}..{hi_w[0]:.1f}, Y {lo_w[1]:.1f}..{hi_w[1]:.1f}, "
              f"Z {lo_w[2]:.1f}..{hi_w[2]:.1f}**. CLAUDE.md states X {claude_lo[0]:.0f}..{claude_hi[0]:.0f}, "
              f"Y {claude_lo[1]:.0f}..{claude_hi[1]:.0f}, Z {claude_lo[2]:.0f}..{claude_hi[2]:.0f}: "
              f"{'agrees' if ok else 'DISAGREES'}. The CAE rotation of -90 degrees about Z maps the domain's local +X "
              "(the flow direction in the lattice) to world -Y, so the inlet face is at world Y "
              f"{hi_w[1]:.0f} and the outlet at Y {lo_w[1]:.0f}.")
    record("Domain recomputed from source agrees with CLAUDE.md", "PASS" if ok and agree else "FAIL",
           f"X {lo_w[0]:.1f}..{hi_w[0]:.1f}, Y {lo_w[1]:.1f}..{hi_w[1]:.1f}, Z {lo_w[2]:.1f}..{hi_w[2]:.1f}")
    return lo_w, hi_w


# -------------------------------------------------------------------------------------------------
# 3. Environment bounds and containment
# -------------------------------------------------------------------------------------------------
def env_parts(stage):
    from pxr import Usd, UsdGeom
    xf = UsdGeom.XformCache()
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                              useExtentsHint=False)
    parts = {}
    for prim in Usd.PrimRange(stage.GetPrimAtPath("/World/WindTunnel")):
        if not prim.IsA(UsdGeom.Gprim) or not renderable(prim):
            continue
        rng = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if rng.IsEmpty():
            continue
        pts = world_points(prim, xf) if prim.IsA(UsdGeom.PointBased) else None
        parts[str(prim.GetPath())] = {"prim": prim, "lo": np.array(rng.GetMin()), "hi": np.array(rng.GetMax()),
                                      "pts": pts}
    return parts, cache


def by_name(parts, name):
    for p, v in parts.items():
        if p.rsplit("/", 1)[-1] == name:
            return v
    return None


def check_environment(stage, dom_lo, dom_hi):
    md.append("\n## 3. Environment bounds and containment\n")
    parts, cache = env_parts(stage)
    rng = cache.ComputeWorldBound(stage.GetPrimAtPath("/World/WindTunnel")).ComputeAlignedRange()
    env_lo, env_hi = np.array(rng.GetMin()), np.array(rng.GetMax())
    md.append(f"- World bound of `/World/WindTunnel` (BBoxCache, useExtentsHint=False, purposes default+render): "
              f"{fmt(env_lo)}..{fmt(env_hi)}, from {len(parts)} renderable gprims.")

    # Authored extents vs actual points (a stale extent silently corrupts every bound above).
    worst = (0.0, "")
    for p, v in parts.items():
        if v["pts"] is None:
            continue
        d = max(np.abs(v["pts"].min(0) - v["lo"]).max(), np.abs(v["pts"].max(0) - v["hi"]).max())
        if d > worst[0]:
            worst = (float(d), p)
    ext_ok = worst[0] < 0.01
    md.append(f"- Authored extents agree with the points of every environment mesh: largest disagreement "
              f"{worst[0]:.4f} cm{(' on `' + worst[1] + '`') if worst[1] else ''}.")
    record("Environment authored extents match their points", "PASS" if ext_ok else "FAIL", f"{worst[0]:.4f} cm")

    inside = bool(np.all(env_lo[:2] <= dom_lo[:2]) and np.all(env_hi >= dom_hi))
    md.append(f"- The environment bound encloses the domain in X, Y and Z-top: {inside} (the domain floor at Z "
              f"{dom_lo[2]:.1f} sits {0 - dom_lo[2]:.1f} cm below the floor top, see below).")

    # Gprim AABBs against the domain.
    md.append("\nEvery renderable environment gprim against the domain box (AABB):\n")
    md.append("| Prim | world AABB (cm) | separation from domain dX, dY, dZ (cm) | status |\n|---|---|---|---|")
    clash = []
    for p, v in sorted(parts.items()):
        g, n = aabb_gap(v["lo"], v["hi"], dom_lo, dom_hi)
        short = p.replace("/World/WindTunnel/", "")
        if n > 0:
            status = "clear"
        elif "/Floor/" in p and v["hi"][2] <= FLOOR_ALLOWANCE_Z:
            status = f"overlaps only below Z {v['hi'][2]:.2f} (floor insert, allowed)"
        else:
            status = "**INTERSECTS**"
            clash.append(short)
        md.append(f"| `{short}` | {fmt(v['lo'])}..{fmt(v['hi'])} | {fmt(g)} | {status} |")
    record("No environment geometry inside the domain (floor inserts below Z 0.5 allowed)",
           "PASS" if not clash else "FAIL", ", ".join(clash) or "none")

    floor = by_name(parts, "Slab")
    if floor is not None:
        top = floor["hi"][2]
        md.append(f"\n- Floor slab top: Z {top:.2f}. Domain bottom: Z {dom_lo[2]:.2f}, i.e. {top - dom_lo[2]:.2f} cm "
                  "below the floor. The lattice's bottom layer is inside the slab. This is the blueprint's own offset "
                  "(the car's tyres touch Z 0, section 4), not something a replacement environment can change; it is "
                  "reported, not failed.")

    # Jet window: project the domain cross-section along Y and measure against the nozzle and collector openings.
    md.append("\nJet window (the domain's X-Z cross-section, extruded along Y, against the tunnel hardware):\n")
    md.append("| Part | Y faces (cm) | gap along Y to the domain (cm) | min X-Z clearance, domain section to "
              "the opening (cm) | vertices inside the section |\n|---|---|---|---|---|")
    jet_ok = True
    missing = []
    for name, face in (("Nozzle", "min"), ("Collector", "max")):
        v = by_name(parts, name)
        if v is None or v["pts"] is None:
            md.append(f"| {name} | not found | | | |")
            missing.append(name)
            continue
        P = v["pts"]
        dist = rect_dist(P[:, 0], P[:, 2], (dom_lo[0], dom_hi[0]), (dom_lo[2], dom_hi[2]))
        n_in = int((dist == 0).sum())
        gap_y = v["lo"][1] - dom_hi[1] if face == "min" else dom_lo[1] - v["hi"][1]
        md.append(f"| {name} | {v['lo'][1]:.1f}..{v['hi'][1]:.1f} | {gap_y:.1f} | {dist.min():.1f} | {n_in} |")
        jet_ok &= gap_y > 0 and n_in == 0 and dist.min() > 0
    md.append("\nThe Y gap is measured from the nozzle mesh's most downstream point (the rolled lip) and from the "
              "collector mesh's most upstream point. The X-Z clearance is the distance from each mesh vertex to the "
              "domain's X-Z rectangle, i.e. vertex-based: chords on the rounded corners sit inside the true arc by at "
              "most the sagitta, well under 1 mm at the current tessellation. Both parts must be found for this check "
              "to pass.")
    record("Domain sits inside the jet (nozzle exit and collector openings, with clearance)",
           "FAIL" if missing else ("PASS" if jet_ok else "FAIL"),
           f"not found: {', '.join(missing)}" if missing else "")

    # Lights: the replacement must bring its own; the blueprint stage layers carry none.
    from pxr import UsdLux
    lights = [p for p in stage.Traverse() if p.HasAPI(UsdLux.LightAPI)]
    ours = [p for p in lights if str(p.GetPath()).startswith("/World/WindTunnel/")]
    other = [str(p.GetPath()) for p in lights if p not in ours]
    md.append(f"\n- Lights on the composed, fully loaded stage: {len(lights)}; under `/World/WindTunnel`: {len(ours)} "
              f"({', '.join(f'{n} {k}' for k, n in sorted(Counter(p.GetTypeName() for p in ours).items()))}); "
              f"elsewhere: {other or 'none'}.")
    record("Environment brings its own lights; none come from elsewhere in the stage",
           "PASS" if ours and not other else "FAIL", f"{len(ours)} ours, {len(other)} other")

    # The blueprint controller discovers prims by applied schema; the environment must not carry any of its schemas.
    from pxr import Usd
    bp_schemas = sorted({f"{p.GetPath()}: {s}" for p in Usd.PrimRange(stage.GetPrimAtPath("/World/WindTunnel"))
                         for s in p.GetAppliedSchemas() if s.startswith(("Rtwt", "Cae", "OmniSci"))})
    md.append(f"- Blueprint schemas (`Rtwt*`, `Cae*`, `OmniSci*`) applied under `/World/WindTunnel`: "
              f"{bp_schemas or 'none'}.")
    record("Environment carries no blueprint (Rtwt/Cae/OmniSci) schemas", "PASS" if not bp_schemas else "FAIL",
           f"{len(bp_schemas)}")
    return parts


# -------------------------------------------------------------------------------------------------
# 4. Car
# -------------------------------------------------------------------------------------------------
def check_car(stage, parts, dom_lo, dom_hi):
    from pxr import Sdf, Usd, UsdGeom

    md.append("\n## 4. Hero car against the floor, turntable, belt and domain\n")
    base = STAGES / "Base.usda"
    bl = Sdf.Layer.FindOrOpen(str(base))
    cs = bl.GetPrimAtPath("/World/CarHero")
    t = tuple(cs.attributes["xformOp:translate"].default)
    r = tuple(cs.attributes["xformOp:rotateXYZ"].default)
    anc = [r'def "CarHero"']
    src_ok = np.allclose(t, CLAUDE_CAR["translate"]) and np.allclose(r, CLAUDE_CAR["rotateXYZ"])
    md.append(f"- `/World/CarHero` translate {fmt(t)} ({cite(base, anc + ['xformOp:translate'])}), rotateXYZ "
              f"{fmt(r)} ({cite(base, anc + ['xformOp:rotateXYZ'])}); CLAUDE.md agrees: {src_ok}.")
    record("CarHero transform in source agrees with CLAUDE.md", "PASS" if src_ok else "FAIL")

    car = stage.GetPrimAtPath("/World/CarHero")
    geo = STAGES / "layers" / "CarHero" / "ConceptCar" / "ConceptCar01.usd"
    if not car or not car.GetChildren() or is_lfs_pointer(geo):
        md.append(f"- Car geometry not available (`{rel(geo)}` is missing or an LFS pointer). Not checked.")
        record("Car bounds", "NOT CHECKED", "CarHero geometry not fetched")
        return None
    md.append(f"- Variant selections: {dict((n, car.GetVariantSets().GetVariantSelection(n)) for n in car.GetVariantSets().GetNames())}.")
    xf = UsdGeom.XformCache()
    pts, wheels, stale = [], {}, []
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                              useExtentsHint=False)
    for prim in Usd.PrimRange(car):
        if not prim.IsA(UsdGeom.PointBased) or not renderable(prim):
            continue
        w = world_points(prim, xf)
        if w is None:
            continue
        pts.append(w)
        b = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        d = max(np.abs(np.array(b.GetMin()) - w.min(0)).max(), np.abs(np.array(b.GetMax()) - w.max(0)).max())
        if d > 1.0:
            stale.append((d, str(prim.GetPath())))
        m = re.search(r"/Wheels/(wheel_[A-Za-z]+)/", str(prim.GetPath()))
        if m:
            wheels.setdefault(m.group(1), []).append(w)
    P = np.concatenate(pts)
    lo, hi = P.min(0), P.max(0)
    bb = cache.ComputeWorldBound(car).ComputeAlignedRange()
    stale.sort(reverse=True)
    md.append(f"- Car world bound from its {len(P):,} visible points: **{fmt(lo)}..{fmt(hi)}**, so "
              f"{hi[1] - lo[1]:.1f} long (Y), {hi[0] - lo[0]:.1f} wide (X), {hi[2] - lo[2]:.1f} tall (Z).")
    md.append(f"- BBoxCache on the same prim gives {fmt(bb.GetMin())}..{fmt(bb.GetMax())}. It reads the authored "
              f"`extent` of each mesh, and {len(stale)} car meshes carry extents that disagree with their points by "
              f"more than 1 cm (worst {stale[0][0]:.1f} cm on `{stale[0][1]}`)." if stale else
              f"- BBoxCache on the same prim gives {fmt(bb.GetMin())}..{fmt(bb.GetMax())}.")
    if stale:
        md.append("  The car bounds in this report are therefore taken from the points, not from BBoxCache. "
                  "Anything else that frames or culls on the car's extents inherits the stale values.")

    car_in = bool(np.all(lo >= dom_lo) and np.all(hi <= dom_hi))
    md.append(f"- Car inside the domain: {car_in}. Clearances: sides {lo[0] - dom_lo[0]:.1f} / {dom_hi[0] - hi[0]:.1f}, "
              f"nose to inlet (Y +) {dom_hi[1] - hi[1]:.1f}, tail to outlet (Y -) {lo[1] - dom_lo[1]:.1f}, roof to "
              f"domain top {dom_hi[2] - hi[2]:.1f}, lowest point {lo[2]:.2f} vs domain floor {dom_lo[2]:.1f}.")
    record("Car inside the domain", "PASS" if car_in else "FAIL")

    # Wheels: contact, track, wheelbase.
    wb = {}
    for k, ws in sorted(wheels.items()):
        W = np.concatenate(ws)
        wb[k] = (W.min(0), W.max(0))
    if wb:
        md.append("\n| Wheel | world AABB (cm) | lowest Z |\n|---|---|---|")
        for k, (a, b) in wb.items():
            md.append(f"| `{k}` | {fmt(a)}..{fmt(b)} | {a[2]:.2f} |")
    centres_y = sorted(((a[1] + b[1]) / 2 for a, b in wb.values()))
    axle_r = np.mean(centres_y[:2]) if len(centres_y) == 4 else None
    axle_f = np.mean(centres_y[2:]) if len(centres_y) == 4 else None
    mid_wb = (axle_r + axle_f) / 2 if axle_r is not None else None
    bbox_cy = (lo[1] + hi[1]) / 2
    inner_track = min(min(abs(a[0]), abs(b[0])) for a, b in wb.values()) if wb else None
    if mid_wb is not None:
        md.append(f"\n- Axles at Y {axle_r:.1f} (rear) and {axle_f:.1f} (front): wheelbase {axle_f - axle_r:.1f}, "
                  f"mid-wheelbase **Y {mid_wb:.1f}**. Bounding-box centre **Y {bbox_cy:.1f}**, X {(lo[0] + hi[0]) / 2:.1f}. "
                  f"The car's own origin is at Y {t[1]:.0f} (CarHero translate), which is at the front axle, not the "
                  "middle of the car. The nose points to +Y (upstream, into the jet).")

    # Floor, turntable and belt from our geometry.
    slab, tt, ring, belt, frame = (by_name(parts, n) for n in
                                   ("Slab", "Turntable", "TurntableRing", "RollingRoadBelt", "RollingRoadFrame"))
    if slab is not None:
        md.append(f"- Lowest car point Z {lo[2]:.2f} against the floor top Z {slab['hi'][2]:.2f}.")
    if ring is not None and tt is not None:
        cx, cy = (ring["lo"][0] + ring["hi"][0]) / 2, (ring["lo"][1] + ring["hi"][1]) / 2
        rad = (ring["hi"][0] - ring["lo"][0]) / 2
        rmax = float(np.hypot(P[:, 0] - cx, P[:, 1] - cy).max())
        md.append(f"- Turntable (from `TurntableRing` geometry): centre ({cx:.1f}, {cy:.1f}), outer radius {rad:.1f}, "
                  f"disc top Z {tt['hi'][2]:.2f}, ring top Z {ring['hi'][2]:.2f}.")
        md.append(f"- Car footprint: farthest point {rmax:.1f} from the turntable centre, so the car sits on the "
                  f"turntable with {rad - rmax:.1f} to spare.")
        record("Car footprint inside the turntable", "PASS" if rmax < rad else "FAIL",
               f"{rmax:.1f} of {rad:.1f}")
        off_mid = (mid_wb - cy) if mid_wb is not None else None
        off_box = bbox_cy - cy
        centred = off_mid is not None and abs(off_mid) <= 10.0
        md.append(f"- Turntable centre against the car: mid-wheelbase is {off_mid:+.1f} from it, bounding-box centre "
                  f"{off_box:+.1f}. A turntable is centred on the car (plan, 'Floor'), so this is **off by about "
                  f"{abs(off_mid):.0f} cm**." if off_mid is not None and not centred else
                  f"- Turntable centre against the car: mid-wheelbase offset {off_mid:+.1f}, bounding-box centre offset "
                  f"{off_box:+.1f}.")
        record("Turntable centred on the car (mid-wheelbase within 10 cm)", "PASS" if centred else "FAIL",
               f"turntable Y {cy:.1f}, mid-wheelbase Y {mid_wb:.1f}" if mid_wb is not None else "")
        tyre_low = min(a[2] for a, b in wb.values()) if wb else lo[2]
        md.append(f"- Tyre contact: lowest tyre point Z {tyre_low:.2f}, turntable disc top Z {tt['hi'][2]:.2f}: the "
                  f"contact patches sink {tt['hi'][2] - tyre_low:.2f} cm into the disc surface. That is a cosmetic "
                  "millimetre-scale overlap, hidden under the tyre.")
    if belt is not None:
        bx = (belt["lo"][0] + belt["hi"][0]) / 2
        fr_hw = ((frame["hi"][0] - frame["lo"][0]) / 2) if frame is not None else (belt["hi"][0] - belt["lo"][0]) / 2
        over = (np.abs(P[:, 0] - bx) <= fr_hw) & (P[:, 1] >= belt["lo"][1]) & (P[:, 1] <= belt["hi"][1])
        under = float(P[over, 2].min()) if over.any() else None
        md.append(f"- Rolling-road belt: X {belt['lo'][0]:.1f}..{belt['hi'][0]:.1f}, Y {belt['lo'][1]:.1f}.."
                  f"{belt['hi'][1]:.1f}, top Z {belt['hi'][2]:.2f}; with its frame it is {2 * fr_hw:.1f} wide. "
                  + (f"The inner tyre faces are at |X| {inner_track:.1f}, so the belt and frame run between the "
                     f"wheels with {inner_track - fr_hw:.1f} to spare each side. " if inner_track else "")
                  + (f"Lowest car point above the belt footprint: Z {under:.1f} (underbody clearance over the belt "
                     f"{under - belt['hi'][2]:.1f})." if under is not None else ""))
        covers = belt["lo"][1] <= lo[1] and belt["hi"][1] >= hi[1]
        md.append(f"- The belt spans the car's full length (Y {lo[1]:.1f}..{hi[1]:.1f}): {covers}.")
        record("Belt runs between the wheels and spans the car", "PASS" if (inner_track is None or inner_track > fr_hw)
               and covers else "FAIL")

    # Wheel-drive belts: each tyre's contact patch (its points within 2 cm of its lowest point) must lie
    # on one of the four wheel belts. The four units are one mesh; split its points by side and axle.
    wbelt = by_name(parts, "WheelBelts")
    if wbelt is None or wbelt["pts"] is None:
        md.append("- Wheel-drive belts: not found in the environment.")
        record("Each tyre contact patch lies on a wheel-drive belt", "FAIL", "WheelBelts not found")
    elif len(wheels) != 4:
        record("Each tyre contact patch lies on a wheel-drive belt", "NOT CHECKED", f"{len(wheels)} wheels found")
    else:
        Q = wbelt["pts"]
        mid_y = mid_wb if mid_wb is not None else (lo[1] + hi[1]) / 2
        units = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                q = Q[(np.sign(Q[:, 0]) == sx) & (np.sign(Q[:, 1] - mid_y) == sy)]
                if len(q):
                    units.append((q.min(0), q.max(0)))
        md.append("\n| Wheel | contact patch X, Y (cm) | wheel belt X, Y (cm) | margin to belt edge (cm) |"
                  "\n|---|---|---|---|")
        all_on = len(units) == 4
        for k, ws in sorted(wheels.items()):
            W = np.concatenate(ws)
            cp = W[W[:, 2] <= W[:, 2].min() + 2.0][:, :2]
            plo, phi = cp.min(0), cp.max(0)
            best = None
            for ulo, uhi in units:
                margin = float(min((plo - ulo[:2]).min(), (uhi[:2] - phi).min()))
                if best is None or margin > best[0]:
                    best = (margin, ulo, uhi)
            all_on &= best is not None and best[0] >= 0
            md.append(f"| `{k}` | {plo[0]:.1f}..{phi[0]:.1f}, {plo[1]:.1f}..{phi[1]:.1f} | "
                      f"{best[1][0]:.1f}..{best[2][0]:.1f}, {best[1][1]:.1f}..{best[2][1]:.1f} | {best[0]:.1f} |")
        md.append(f"\n- Wheel-drive belts: {len(units)} units, top Z {wbelt['hi'][2]:.2f}. Each tyre's contact patch is "
                  "taken as its points within 2 cm of its lowest point. The units are fixed at this car's track and "
                  "wheelbase; a real five-belt rolling road moves them to suit each car.")
        record("Each tyre contact patch lies on a wheel-drive belt", "PASS" if all_on else "FAIL",
               f"{len(units)} units")
    return {"lo": lo, "hi": hi, "mid_wb": mid_wb, "bbox_cy": bbox_cy}


# -------------------------------------------------------------------------------------------------
# 5. Cameras
# -------------------------------------------------------------------------------------------------
def mesh_tris(prim, xf):
    """World-space triangles of a mesh (polygons fan-triangulated), shape (N, 3, 3)."""
    from pxr import UsdGeom
    mesh = UsdGeom.Mesh(prim)
    P = world_points(prim, xf)
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), int)
    idx = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), int)
    tris, o = [], 0
    for c in counts:
        f = idx[o:o + c]
        for k in range(1, c - 1):
            tris.append((f[0], f[k], f[k + 1]))
        o += c
    return P[np.array(tris)]


def point_tri_dist(p, tris):
    """Exact distance from point p to each triangle of a soup (N, 3, 3), via the closest point on the
    triangle (Voronoi-region method, Ericson, Real-Time Collision Detection 5.1.5)."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = np.einsum("ij,ij->i", ab, ap), np.einsum("ij,ij->i", ac, ap)
    bp = p - b
    d3, d4 = np.einsum("ij,ij->i", ab, bp), np.einsum("ij,ij->i", ac, bp)
    cp = p - c
    d5, d6 = np.einsum("ij,ij->i", ab, cp), np.einsum("ij,ij->i", ac, cp)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        v_in, w_in = vb / denom, vc / denom
        q = a + ab * v_in[:, None] + ac * w_in[:, None]                       # interior
        t_ab = d1 / (d1 - d3)
        t_ac = d2 / (d2 - d6)
        t_bc = (d4 - d3) / ((d4 - d3) + (d5 - d6))
    m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    q = np.where(m[:, None], b + (c - b) * t_bc[:, None], q)                 # edge BC
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    q = np.where(m[:, None], a + ac * t_ac[:, None], q)                      # edge AC
    q = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, q)                    # vertex C
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    q = np.where(m[:, None], a + ab * t_ab[:, None], q)                      # edge AB
    q = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, q)                    # vertex B
    q = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, q)                     # vertex A
    return np.linalg.norm(p - q, axis=1)


def ray_crossings(tris, origin, d):
    """Count crossings of a ray with a triangle soup (Moller-Trumbore)."""
    d = np.asarray(d, float)
    v0, e1, e2 = tris[:, 0], tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    tv = origin - v0
    u = np.einsum("ij,ij->i", tv, pv) * inv
    qv = np.cross(tv, e1)
    v = (qv @ d) * inv
    t = np.einsum("ij,ij->i", e2, qv) * inv
    return int(np.count_nonzero(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9)))


def classify_point(tris, p):
    """'material' (inside the solid), 'opening' (enclosed by the shell on +Z, +X and -X: clear air inside a
    duct), or 'air'. The origin is nudged off any symmetry plane so a ray never grazes a shared edge."""
    o = np.asarray(p, float) + np.array([1.2345e-3, 2.3456e-3, 3.4567e-3])
    up, px, nx = (ray_crossings(tris, o, d) for d in ((0, 0, 1), (1, 0, 0), (-1, 0, 0)))
    if up % 2 == 1 and px % 2 == 1:
        return "material", (up, px, nx)
    if up % 2 != px % 2:
        return "ambiguous", (up, px, nx)
    if up >= 2 and px >= 2 and nx >= 2:
        return "opening", (up, px, nx)
    return "air", (up, px, nx)


def xform_times(prim):
    from pxr import UsdGeom
    times = set()
    p = prim
    while p and not p.IsPseudoRoot():
        x = UsdGeom.Xformable(p)
        if x:
            for op in x.GetOrderedXformOps():
                times.update(op.GetAttr().GetTimeSamples())
        p = p.GetParent()
    return sorted(times)


def check_cameras(stage, parts, car, dom_lo, dom_hi):
    from pxr import Gf, Sdf, Usd, UsdGeom

    md.append("\n## 5. Blueprint cameras\n")
    camf = STAGES / "layers" / "Cameras.usda"
    cl = Sdf.Layer.FindOrOpen(str(camf))
    ms = cl.GetPrimAtPath("/World/Cameras/CameraMAIN_00")
    vals = {k: ms.attributes[k].default for k in ("xformOp:translate", "xformOp:rotateYXZ", "focalLength",
                                                  "horizontalAperture", "verticalAperture")}
    anc = [r'def Camera "CameraMAIN_00"']
    ok = (np.allclose(vals["xformOp:translate"], CLAUDE_CAM["translate"], atol=0.06)
          and np.allclose(vals["xformOp:rotateYXZ"], CLAUDE_CAM["rotateYXZ"], atol=0.006)
          and abs(vals["focalLength"] - CLAUDE_CAM["focalLength"]) < 0.006
          and abs(vals["horizontalAperture"] - CLAUDE_CAM["horizontalAperture"]) < 1e-3
          and abs(vals["verticalAperture"] - CLAUDE_CAM["verticalAperture"]) < 0.006)
    md.append(f"- `CameraMAIN_00` in source: translate {fmt(vals['xformOp:translate'], 2)} "
              f"({cite(camf, anc + ['xformOp:translate'])}), rotateYXZ {fmt(vals['xformOp:rotateYXZ'], 3)} "
              f"({cite(camf, anc + ['xformOp:rotateYXZ'])}), focal {vals['focalLength']:.4f} "
              f"({cite(camf, anc + ['focalLength'])}), aperture {vals['horizontalAperture']:.3f} x "
              f"{vals['verticalAperture']:.4f} ({cite(camf, anc + ['horizontalAperture'])}, "
              f"{cite(camf, anc + ['verticalAperture'])}). CLAUDE.md agrees to its stated precision: {ok}.")
    record("CameraMAIN_00 values in source agree with CLAUDE.md", "PASS" if ok else "FAIL")

    names = {"Nozzle": "nozzle", "Collector": "collector", "Turntable": "turntable", "RollingRoadBelt": "belt",
             "Honeycomb": "honeycomb", "Ceiling": "ceiling", "WallLeft": "left wall", "WallRight": "right wall",
             "WallUpstream": "upstream wall", "WallDownstream": "downstream wall", "LightPanels": "light panels"}
    tagged = {lab: by_name(parts, n) for n, lab in names.items() if by_name(parts, n) is not None}
    env_lo = np.min([v["lo"] for v in parts.values()], 0)
    env_hi = np.max([v["hi"] for v in parts.values()], 0)
    hall = [v for p, v in parts.items() if "/Hall/" in p and "LightPanels" not in p]
    car_c = Gf.Vec3d(*((car["lo"] + car["hi"]) / 2)) if car else Gf.Vec3d(0, 250, 70)

    md.append("\n| Camera | samples (time range) | position range (cm) | in an environment gprim AABB "
              "(samples, classification) | inside the hall | car centre in view | distance to car centre | "
              "in view (first sample) |\n|---|---|---|---|---|---|---|---|")
    any_out, in_material, in_opening = [], [], []
    xf = UsdGeom.XformCache()
    tri_cache = {}
    cams = [p for p in stage.Traverse() if p.IsA(UsdGeom.Camera)]
    got = sorted(c.GetName() for c in cams)
    record("All expected blueprint cameras loaded", "PASS" if got == sorted(EXPECTED_CAMERAS) else "FAIL",
           f"{len(got)} of {len(EXPECTED_CAMERAS)}"
           + (f"; missing {sorted(set(EXPECTED_CAMERAS) - set(got))}, extra {sorted(set(got) - set(EXPECTED_CAMERAS))}"
              if got != sorted(EXPECTED_CAMERAS) else ""))
    all_pos = []  # (camera, position) for every sample
    for cam in cams:
        times = xform_times(cam)
        tcs = [Usd.TimeCode(t) for t in times] if times else [Usd.TimeCode.Default()]
        pos, out, inview, dists = [], 0, 0, []
        hits = {}   # part -> Counter(classification)
        first_view = None
        for tc in tcs:
            gc = UsdGeom.Camera(cam).GetCamera(tc)
            fr = gc.frustum
            m = gc.transform
            p = np.array(m.ExtractTranslation())
            pos.append(p)
            all_pos.append((cam.GetName(), p))
            for path, v in parts.items():
                if np.all(p >= v["lo"]) and np.all(p <= v["hi"]):
                    short = path.replace("/World/WindTunnel/Geometry/", "")
                    if v["prim"].IsA(UsdGeom.Mesh):
                        if path not in tri_cache:
                            tri_cache[path] = mesh_tris(v["prim"], xf)
                        kind, _ = classify_point(tri_cache[path], p)
                    else:
                        kind = "not a mesh, AABB only"
                    hits.setdefault(short, Counter())[kind] += 1
                    t_val = tc.GetValue() if not tc.IsDefault() else float("nan")
                    if kind in ("material", "ambiguous", "not a mesh, AABB only"):
                        in_material.append((cam.GetName(), short, t_val, p))
                    elif kind == "opening":
                        in_opening.append((cam.GetName(), short, t_val, p))
            if hall:
                # Interior of the hall: inside the env bound and not inside any wall slab.
                if not (np.all(p > env_lo) and np.all(p < env_hi)):
                    out += 1
            if fr.Intersects(car_c):
                inview += 1
            dists.append(float(np.linalg.norm(p - np.array(car_c))))
            if first_view is None:
                first_view = [lab for lab, v in tagged.items()
                              if fr.Intersects(Gf.BBox3d(Gf.Range3d(Gf.Vec3d(*v["lo"]), Gf.Vec3d(*v["hi"]))))]
        P = np.array(pos)
        rng_t = f"{len(tcs)} ({times[0]:g}..{times[-1]:g})" if times else "static"
        if out:
            any_out.append(str(cam.GetPath()))
        hit_txt = "; ".join(f"`{k}`: " + ", ".join(f"{n} {c}" for c, n in sorted(cnt.items()))
                            for k, cnt in sorted(hits.items())) or "none"
        md.append(f"| `{cam.GetName()}` | {rng_t} | {fmt(P.min(0))}..{fmt(P.max(0))} | {hit_txt} | "
                  f"{'yes' if not out else f'NO at {out} sample(s)'} | "
                  f"{100 * inview / len(tcs):.0f}% of samples | {min(dists):.0f}..{max(dists):.0f} | "
                  f"{', '.join(first_view) or 'nothing tagged'} |")
    md.append("\nMethod: every camera position (one per authored transform time sample) is tested against each "
              "renderable environment gprim's world AABB. A position inside an AABB is then classified against that "
              "mesh with ray parity (+Z, +X and -X rays): **material** means inside the solid, **opening** means "
              "enclosed by the shell above and on both sides, i.e. clear air inside the nozzle or collector duct, and "
              "**air** means clear air that only falls inside the box. 'In view' is a frustum-against-AABB test: the "
              "part's box enters the frustum, which says nothing about occlusion.")
    record("No camera position inside solid environment geometry (every time sample)",
           "PASS" if not in_material else "FAIL",
           "; ".join(sorted({f"{c} in {s}" for c, s, _, _ in in_material})) or f"{len(cams)} cameras")
    CAMERA_OPENING[:] = in_opening
    if in_opening:
        md.append("\nCamera samples inside a duct opening:\n")
        md.append("| Camera | part | samples | time range | Y range (cm) | X range | Z |\n|---|---|---|---|---|---|---|")
        groups = {}
        for c, s, t, p in in_opening:
            groups.setdefault((c, s), []).append((t, p))
        for (c, s), items in sorted(groups.items()):
            ts = [t for t, _ in items]
            Pp = np.array([p for _, p in items])
            md.append(f"| `{c}` | `{s}` | {len(items)} | {min(ts):g}..{max(ts):g} | {Pp[:, 1].min():.1f}.."
                      f"{Pp[:, 1].max():.1f} | {Pp[:, 0].min():.1f}..{Pp[:, 0].max():.1f} | "
                      f"{Pp[:, 2].min():.1f}..{Pp[:, 2].max():.1f} |")
        noz = by_name(parts, "Nozzle")
        if noz is not None and any(s.endswith("Nozzle") for _, s, _, _ in in_opening):
            global NOZZLE_LIP_Y
            NOZZLE_LIP_Y = float(noz["lo"][1])
            ymax = max(p[1] for c, s, t, p in in_opening if s.endswith("Nozzle"))
            md.append(f"\nThese blueprint camera paths were authored for an environment with nothing at this spot. "
                      f"The most upstream sample inside the nozzle mouth is at Y {ymax:.1f}, against the nozzle's most "
                      f"downstream point (the lip) at Y {noz['lo'][1]:.1f}. At those frames the camera sits inside "
                      "the contraction, looking downstream past the exit lip, which then fills the frame edges.")
    record("No camera passes inside the nozzle or collector opening", "PASS" if not in_opening else "FAIL",
           "; ".join(sorted({f"{c} ({s.rsplit('/', 1)[-1]})" for c, s, _, _ in in_opening})))
    record("Every camera stays inside the hall", "PASS" if not any_out else "FAIL", ", ".join(any_out) or "")
    noz = by_name(parts, "Nozzle")
    if noz is not None:
        lip = float(noz["lo"][1])
        front = [(c, p) for c, p in all_pos
                 if noz["lo"][0] <= p[0] <= noz["hi"][0] and p[2] <= noz["hi"][2]]
        if front:
            c_min, p_min = min(front, key=lambda cp: lip - cp[1][1])
            gap = lip - p_min[1]
            md.append(f"\nNozzle lip clearance along Y: of the camera samples that fall within the nozzle's width and "
                      f"height ({len(front)}), the most upstream is `{c_min}` at Y {p_min[1]:.1f}, {gap:.1f} cm "
                      f"downstream of the plane of the lip (the nozzle mesh's most downstream point, Y {lip:.1f}). "
                      "This is a separation along Y only, not a distance to the surface.")
            record("Every camera sample in front of the nozzle stays >= 30 cm downstream of its lip plane (Y)",
                   "PASS" if gap >= 30.0 else "FAIL", f"closest {gap:.1f} cm along Y ({c_min})")
        # True minimum distance from every camera sample to the nozzle surface (its triangles).
        if noz["prim"].IsA(UsdGeom.Mesh):
            tris = tri_cache.get(str(noz["prim"].GetPath()))
            if tris is None:
                tris = mesh_tris(noz["prim"], xf)
            best = (math.inf, None, None)
            for c, p in all_pos:
                g, n_aabb = aabb_gap(p, p, noz["lo"], noz["hi"])
                if n_aabb >= best[0]:
                    continue   # the box is already farther than the best surface distance
                d = float(point_tri_dist(p, tris).min())
                if d < best[0]:
                    best = (d, c, p)
            d, c, p = best
            md.append(f"\nNozzle surface clearance: the exact minimum distance from any camera sample ({len(all_pos)} "
                      f"samples, all cameras) to the nozzle mesh's {len(tris):,} triangles is **{d:.1f} cm**, "
                      f"`{c}` at {fmt(p)}. Samples are the authored transform time samples; the path between two "
                      "samples is not swept.")
            record("Every camera sample stays >= 30 cm from the nozzle surface (exact point-to-mesh distance)",
                   "PASS" if d >= 30.0 else "FAIL", f"closest {d:.1f} cm ({c})")

    # Gprims that ride along under the camera prims (Kit viewport camera models).
    cg = [p for p in Usd.PrimRange(stage.GetPrimAtPath("/World/Cameras")) if p.IsA(UsdGeom.Gprim)]
    vis = [p for p in cg if renderable(p)]
    md.append(f"\n- Gprims under `/World/Cameras` (Kit viewport camera models): {len(cg)}, of which "
              f"{len(vis)} are visible with default or render purpose"
              + (f", for example `{vis[0].GetPath()}`. They sit at each camera's own position, so a render from one "
                 "blueprint camera can show the others' camera models." if vis else "."))


# -------------------------------------------------------------------------------------------------
# 6. Blueprint code that addresses the old environment
# -------------------------------------------------------------------------------------------------
CODE_EXT = {".py", ".usda", ".kit", ".toml", ".json", ".js", ".ts"}


def check_references():
    md.append("\n## 6. Blueprint source that addresses the old environment\n")
    names = set()
    for p in OLD_ENV_DIR.rglob("*"):
        if p.suffix in (".usd", ".usda", ".usdc") and ".thumbs" not in p.parts:
            names.add(p.stem)
    names |= {p.name for p in (OLD_ENV_DIR / "prop").iterdir()} if (OLD_ENV_DIR / "prop").is_dir() else set()
    # Drop the asset-pipeline folder names (geometry, material_render, proxy, rig_skel ...): they are
    # generic words, not names of anything in the old environment.
    generic = re.compile(r"^(geometry|material|preview|proxy|rig)(_\w+)?$")
    names = sorted(n for n in names if len(n) >= 4 and not generic.match(n))
    pats = [
        ("path under /World/WindTunnel", re.compile(r"/World/WindTunnel\b")),
        ("WindTunnel prim name", re.compile(r"\bWindTunnel\b")),
        ("old env layer", re.compile(r"windTunnelEnv")),
        ("old env asset name", re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b")) if names else None,
        ("light schema or type", re.compile(r"\b(UsdLux|LightAPI|DomeLight|DistantLight|RectLight|SphereLight|"
                                            r"DiskLight|CylinderLight)\b")),
        ("treadmill / turntable / rolling road", re.compile(r"(?i)\b(treadmill|turntable|rolling[ _]?road)\b")),
        ("monitor", re.compile(r"(?i)\bmonitors?\b")),
        ("ground", re.compile(r"(?i)\bground(?:[ _]?plane)?\b(?![ _-]?truth)")),
    ]
    pats = [p for p in pats if p]
    hits = []
    scanned = 0
    skipped = Counter()   # reason -> count, for files with a scanned extension that were not read
    other_ext = Counter()
    for dirpath, dirnames, filenames in os.walk(BP):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        dp = Path(dirpath)
        if dp == OLD_ENV_DIR or OLD_ENV_DIR in dp.parents:
            continue
        for fn in filenames:
            f = dp / fn
            if f.suffix not in CODE_EXT:
                other_ext[f.suffix.lower() or "(none)"] += 1
                continue
            try:
                if is_lfs_pointer(f):
                    skipped["git-lfs pointer (content not fetched)"] += 1
                    continue
                if f.stat().st_size > 8_000_000:
                    skipped["larger than 8 MB"] += 1
                    continue
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                skipped["unreadable"] += 1
                continue
            scanned += 1
            for i, line in enumerate(text.splitlines(), 1):
                for label, rx in pats:
                    if rx.search(line):
                        hits.append((label, rel(f), i, line.strip()[:160]))
    md.append(f"Scanned {scanned} files (`{', '.join(sorted(CODE_EXT))}`) under `{rel(BP)}`, skipping `.git`, the old "
              f"environment's own directory and LFS pointers. Old environment asset names searched for (from the files "
              f"under `{rel(OLD_ENV_DIR)}`): {', '.join(f'`{n}`' for n in names)}.\n")
    md.append("Scope of this scan, so a reader knows what it cannot see:\n")
    md.append(f"- Files with a scanned extension that were not read: "
              f"{', '.join(f'{n} {k}' for k, n in sorted(skipped.items())) or 'none'}. Binary `.usd`/`.usdc` layers "
              "and any other format are not text-searched.")
    md.append(f"- Files with other extensions, not scanned: {sum(other_ext.values())} "
              f"({', '.join(f'{k} {n}' for k, n in other_ext.most_common(8))}"
              f"{', ...' if len(other_ext) > 8 else ''}).")
    md.append(f"- The old environment itself (`{rel(OLD_ENV_DIR)}`) is skipped on purpose; its root layer "
              "`windTunnelEnv.usd` is an LFS object that was not fetched, so nothing it references was inspected.")
    md.append("- This is a text search for names and paths. A lookup built at run time from pieces, or done by a "
              "Kit extension that is not in this repository, would not be found.\n")
    if not hits:
        md.append("No hits.")
    else:
        md.append("| Pattern | Location | Line |\n|---|---|---|")
        for label, f, i, line in hits:
            md.append(f"| {label} | `{f}:{i}` | `{line.replace('|', '/')}` |")
    addressing = [h for h in hits if h[0] in ("path under /World/WindTunnel", "old env asset name")
                  and not h[1].endswith("stages/Base.usda")]
    only_arc = all(h[1].endswith("stages/Base.usda") for h in hits)
    if addressing:
        md.append("\n**Some files address the old environment's contents; see the table.**")
    else:
        md.append("\nOnly the arc itself names the environment: `Base.usda` defines `/World/WindTunnel` and its payload. "
                  "No Python, Kit, TOML, JSON or USDA file addresses a prim under `/World/WindTunnel` or an old asset by "
                  "name, and nothing selects lights, ground, a treadmill or monitors by type or name."
                  + ("" if only_arc else " The other hits are listed so a reader can confirm they are unrelated."))
    md.append("\nRelated runtime lookups, read by hand: the controller finds prims through `workflow.toml` targets "
              "(`/World/AppState`, `/World/Inference`, `/World/CarHero`, `/World/CarCFD`, `/World/CAE`, "
              "`/World/InferenceResults`), through applied schemas (`RtwtTransformAPI`, control-binding APIs; "
              "`omni.rtwt.controller/python/utils.py`, `validator.py`) and through camera names. None of these "
              "live under `/World/WindTunnel`, and the environment carries no such schema.")
    record("No scanned blueprint source addresses prims inside the old environment",
           "PASS" if not addressing else "FAIL",
           f"{scanned} text files scanned, {sum(skipped.values())} skipped (LFS or large); "
           f"{len(hits)} hit(s) listed, {len(addressing)} addressing")


# -------------------------------------------------------------------------------------------------
def write_report(car):
    head = ["# Fit check: open-jet environment in the blueprint stage\n",
            "Generated by `tools/fit_check.py`. Do not hand-edit; rerun the tool.\n",
            "This is a conceptual presentation environment. The check covers composition, transforms and bounds on "
            "the stage `scenes/blueprint_override.usda` builds. It does not show that the blueprint application runs "
            "with this environment.\n",
            "## Summary\n", "| Check | Result | Detail |", "|---|---|---|"]
    for c, s, d in results:
        head.append(f"| {c} | **{s}** | {d.replace('|', '/')} |")
    nc = ["\n## Not checked\n",
          "- The blueprint application (Kit, the inference service, the streamer). Nothing here launches it.",
          "- The inference geometry: `/World/CarCFD` payloads `data/low_res/detailed_car_*/aero_suv_low.ply`, an LFS "
          "object that was not fetched, and plain OpenUSD has no PLY file format plugin (Kit supplies one). Its "
          "placement relative to the hero car was not measured.",
          "- The original `windTunnelEnv.usd` is an LFS object that was not fetched, so its contents (and anything "
          "it carried that is now gone, such as its own camera or render settings) were not compared.",
          "- Occlusion: 'in view' tests only frustum against box.",
          "- Camera paths between authored time samples: every camera test above uses the samples themselves, "
          "not the swept path between them."]
    if PRIVATE_RENDER.exists():
        import datetime
        when = datetime.date.fromtimestamp(PRIVATE_RENDER.stat().st_mtime).isoformat()
        current = PRIVATE_RENDER.stat().st_mtime >= ASSET.stat().st_mtime
        nc.append(f"- Rendering, partly: the blueprint stage with this override (their `Main.usda`, our environment, "
                  f"their hero car) was rendered locally with ovrtx from their `CameraMAIN_00` on {when}"
                  + ("" if current else ", before the current environment asset was written")
                  + ". That image shows the blueprint's car, so it is kept private (`build/`, untracked) and not "
                  "published. Only `CameraMAIN_00` was rendered; the other blueprint cameras were not.")
    else:
        nc.append("- Rendering from the blueprint cameras: no local render of the blueprint stage with this override "
                  f"was found (`{rel(PRIVATE_RENDER)}`).")
    rec = ["\n## Recommendations\n"]
    centred = any(c.startswith("Turntable centred") and st == "PASS" for c, st, _ in results)
    if car and car.get("mid_wb") is not None and not centred:
        y = round(car["mid_wb"])
        rec.append(f"- Move the turntable to the car: set `CFG[\"turntable\"][\"cy\"]` in `tools/build_env.py` to "
                   f"about **{y}** (mid-wheelbase Y {car['mid_wb']:.1f}; bounding-box centre Y {car['bbox_cy']:.1f}). "
                   "The belt and its frame already follow `cy`. Place the presentation props (Ahmed body, QC spheres) "
                   "at the same Y, so the hero shots and the blueprint car share a centre.")
        rec.append("- After moving it, check the belt ends: with a 450 cm half length the belt then reaches about "
                   f"Y {y + 450}, past the domain inlet at Y 430 and toward the nozzle lip. Shorten `half_len` if the "
                   "belt should stop inside the jet.")
    noz_cams = [p for c, s, t, p in CAMERA_OPENING if s.endswith("Nozzle")]
    if noz_cams and NOZZLE_LIP_Y is not None:
        ymax = max(p[1] for p in noz_cams)
        names = sorted({c for c, s, t, p in CAMERA_OPENING if s.endswith("Nozzle")})
        shift = math.ceil((ymax + 30.0 - NOZZLE_LIP_Y) / 10.0) * 10.0
        rec.append(f"- {', '.join(f'`{n}`' for n in names)} pass through the nozzle mouth (up to Y {ymax:.1f}). To keep "
                   f"every blueprint camera at least 30 cm clear of the lip, move the nozzle upstream by about "
                   f"**{shift:.0f} cm** (`CFG[\"nozzle\"][\"exit_y\"]` and `inlet_y` together, with the honeycomb and "
                   "the end of the centreline). The plan's exit at Y +700 is a nominal figure, and the domain inlet at "
                   "Y 430 leaves room. The alternative is to keep the nozzle and accept those frames, or not to use "
                   "those two blueprint cameras for renders.")
    rec.append("- Leave the floor at Z 0. The domain's 4 cm below the floor is the blueprint's own convention, and the "
               "car's tyres stand on Z 0.")
    rec.append("- Any code that frames or culls the car should compute bounds from points, or ignore the car's "
               "authored extents, which are stale on several meshes.")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(head + [""] + md + nc + rec) + "\n", encoding="utf-8", newline="\n")
    print("wrote", REPORT)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Fit check of the environment in the blueprint stage.")
    ap.add_argument("--strict", action="store_true", help="also exit 1 if any check is NOT CHECKED")
    args = ap.parse_args()
    stage = check_composition()
    dom_lo, dom_hi = check_domain(stage)
    parts = check_environment(stage, dom_lo, dom_hi)
    car = check_car(stage, parts, dom_lo, dom_hi)
    check_cameras(stage, parts, car, dom_lo, dom_hi)
    check_references()
    write_report(car)
    fails = [c for c, s, _ in results if s == "FAIL"]
    unchecked = [c for c, s, _ in results if s == "NOT CHECKED"]
    print(f"\n{len(results)} checks: {len(fails)} FAIL, {len(unchecked)} NOT CHECKED")
    if fails or (args.strict and unchecked):
        print("FIT CHECK FAILED" + (" (--strict: NOT CHECKED counts as a failure)" if args.strict and unchecked
                                    and not fails else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
