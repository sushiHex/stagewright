# Build the open-jet test section environment as models/wind_tunnel/assets/test_section.usda, with its procedural
# textures in models/wind_tunnel/assets/textures/.
#   python tools/build_env.py            build (textures, then the stage), then the containment check
#   python tools/build_env.py check      containment check only, on the existing file
#
# Units: centimetres, Z-up, flow runs along world -Y (nozzle upstream at +Y, collector at -Y).
# Payload root is /Environment with an identity transform; everything, lights included, lives
# under it. Geometry is generated through tools/meshlib.py and authored through usdex.core.
# Textures are computed in Warp and written through nvImageCodec (no downloaded assets), and every material is
# a UsdPreviewSurface whose textures are referenced by paths relative to the asset.
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meshlib as ml  # noqa: E402

from project_paths import ROOT, MODEL

OUT = MODEL / "assets" / "test_section.usda"
TEX_DIR = OUT.parent / "textures"

# ---------------------------------------------------------------------------------------------
# Every dimension lives here (cm).
# ---------------------------------------------------------------------------------------------
CFG = {
    # Blueprint flow domain, world space. Must sit inside the jet.
    "domain": {"x": (-144.0, 144.0), "y": (-650.0, 430.0), "z": (-4.0, 248.0)},
    # The hall runs 100 cm further upstream than downstream, so the settling chamber keeps its
    # depth after the nozzle moved upstream (see "nozzle").
    "hall": {
        "x": (-1200.0, 1200.0), "y": (-1600.0, 1700.0), "z": (0.0, 1200.0),
        "wall_t": 30.0,          # backing slab thickness, outside the interior
        "panel": 300.0,          # target acoustic panel pitch
        "panel_gap": 8.0,        # seam between panels
        "panel_depth": 6.0,      # how far panels stand proud of the backing
        "panel_chamfer": 1.5,
    },
    "floor": {"thick": 30.0, "chamfer": 1.0},
    # Light epoxy test-section floor inset into the darker hall concrete.
    "test_floor": {"x": (-700.0, 700.0), "y": (-1150.0, 1555.0), "top": 0.05, "bottom": -0.5},
    # Exit at Y 775, not the plan's nominal 700: two blueprint camera paths (Camera_ANIM3 and
    # FullOrbit_Camera) reach Y 727.3, and this keeps the lip (exit - wall / 2 = 762.5) 35 cm
    # clear of them (models/wind_tunnel/docs/fit-check.md, section 5). Everything upstream moved with it.
    "nozzle": {
        "exit_y": 775.0, "inlet_y": 1575.0,
        "exit_hw": 325.0, "exit_h": 400.0, "exit_r": 40.0,     # exit 650 x 400 (26 m2)
        "inlet_hw": 650.0, "inlet_h": 800.0, "inlet_r": 160.0,  # contraction ratio 4
        "wall": 25.0,            # shell thickness; the exit lip is a half-round of this diameter
        "stations": 48, "lip_steps": 10, "n_arc": 12,
        "settling_margin": 20.0, # settling chamber flange beyond the inlet outer shell
    },
    # Exit flange: a plate ring just upstream of the lip, bolted on its downstream face.
    "flange": {"width": 38.0, "thick": 8.0, "bolt_offset": 24.0, "bolt_pitch": 20.0,
               "bolt_r": 2.0, "bolt_h": 1.6, "washer_r": 3.0, "washer_h": 0.4},
    # Stiffener ribs: steel plates standing proud of the shell, painted light grey against the
    # white skin. The A-frame supports bear on the first two.
    "nozzle_ribs": {"y": (935.0, 1235.0, 1500.0), "height": 12.0, "half_w": 6.0},
    # Panel seams: circumferential bands between ribs, and longitudinal lines along the profile
    # (the corner tangent lines, side mid-height and roof centre), slightly proud and dark.
    "nozzle_seams": {"y": (860.0, 1085.0, 1370.0), "half_w": 1.2, "proud": 0.35, "embed": 2.0,
                     "long_y": (790.0, 1570.0), "stations": 40},
    # Side supports: per station and side, an A-frame (a post against the shell rib and a
    # splayed raker meeting it high up, tied near the floor), longitudinal X-bracing between the
    # two frames, and base plates. "member" is the square tube section.
    "supports": {"y": (935.0, 1235.0), "member": 22.0, "apex": 0.62, "spread": 0.42, "tie": 0.22,
                 "plate": (60.0, 3.0)},
    # One heavy portal at the settling chamber: two box columns, a header and knee braces.
    "chamber_portal": {"y": 1615.0, "col": 60.0, "depth": 50.0, "header": 60.0, "knee": 160.0},
    "collector_supports": {"y": (-1340.0, -1460.0)},  # bear on the collector ribs
    "honeycomb": {"y": 1555.0, "cell_side": 6.0, "cell_wall": 0.7,  # hex cell (cm), exaggerated to read on camera
                  "frame_w": 10.0, "frame_d": 14.0, "bays_x": 6, "bays_z": 3, "mullion_w": 8.0,
                  "light_y": 1535.0, "light_intensity": 1500.0,  # dim fill so the contraction is not a black hole
                  "key_y": 1325.0, "key_intensity": 2500.0},     # faces the honeycomb from downstream
    "collector": {
        "lip_y": -1100.0,        # most upstream point of the bell mouth
        "throat_hw": 400.0, "throat_h": 500.0, "throat_r": 60.0,  # 800 x 500 intake
        "lip_r": 100.0,          # bell-mouth roll radius
        "diffuser_deg": 3.0,     # diffuser half angle downstream of the throat
        "end_y": -1600.0, "stations": 24, "roll_steps": 16, "n_arc": 12,
        "trim_r": 4.0,           # stainless bead along the lip apex
        "flange_y": -1235.0,     # plate ring where the bell mouth roll meets the outer skin
        "ribs_y": (-1340.0, -1460.0),
        "screen_y": -1585.0,     # safety screen across the diffuser, against the downstream wall
        "screen_pitch": 45.0, "screen_bar": 5.0,
        "face_y": -1212.0, "face_w": 90.0, "face_t": 10.0,  # bulkhead frame around the bell mouth
        "face_bolt_pitch": 60.0,  # visible fasteners on the upstream face of the bulkhead
        "fill_y": -1260.0, "fill_intensity": 900.0,  # dim light inside the throat, facing downstream
    },
    # Centred on the hero car's mid-wheelbase, Y 92.9 (models/wind_tunnel/docs/fit-check.md, section 4).
    "turntable": {"cx": 0.0, "cy": 93.0, "r": 500.0, "ring_w": 12.0, "top": 0.10, "ring_top": 0.15, "bottom": -10.0,
                  "seam_w": 2.5},
    # half_len 380 keeps the belt, its drums and end plates on the turntable (Y -321..507), well
    # inside the jet, while spanning the car (Y -154..351).
    "belt": {"hw": 50.0, "half_len": 380.0, "top": 0.30, "bottom": -3.0, "frame_w": 10.0, "frame_top": 0.25,
             "gap": 1.5, "end_plate": 30.0, "drum_r": 3.0, "drum_gap": 4.0},
    # Wheel-drive belt units of a five-belt rolling road: one short flush belt under each tyre,
    # beside the centre belt, all on the turntable. Unit centres are the blueprint hero car's tyre
    # contact centres, derived from the wheel bounding boxes in models/wind_tunnel/docs/fit-check.md section 4: X is
    # the centre of each wheel's box (front +/-91.7, rear +/-94.5), Y is its axle (front 240.6,
    # rear -54.7). The tyres are 29 (front) to 34 (rear) cm wide, so a 35 x 60 belt covers each
    # contact patch. A real unit slides to suit each car's track and wheelbase; these are fixed at
    # the blueprint car's. Tops stay under Z 0.5 (floor inserts may only enter the domain below it).
    "wheel_belts": {"units": ((-91.7, 240.6), (91.7, 240.6), (-94.5, -54.7), (94.5, -54.7)),
                    "w": 35.0, "l": 60.0, "top": 0.16, "bottom": -3.0, "gap": 0.8,
                    "slot_top": 0.12, "frame_w": 4.0, "frame_top": 0.14},
    # Painted centreline, nozzle to collector, broken where it would cross the turntable.
    "centreline": {"hw": 4.0, "y": (-1090.0, 765.0), "top": 0.20, "turntable_clear": 8.0},
    "lights": {
        "rows_x": (-700.0, -250.0, 250.0, 700.0),
        "cols_y": (-1250.0, -750.0, -250.0, 250.0, 750.0, 1250.0),
        "w": 120.0, "l": 400.0,  # diffuser size in X and Y
        "housing": 8.0,          # housing border around the diffuser
        "panel_z": (1180.0, 1194.0),  # housing; the diffuser face is its underside
        "light_gap": 0.5,        # RectLight sits this far below the diffuser, emitting down (-Z)
        "pool": {"x": 300.0, "y": 800.0},  # lights over the test section, inside |x|, |y|
        "pool_intensity": 6000.0,
        "intensity": 2200.0,
        "dome_intensity": 0.0,   # the hall is closed, so a dome cannot reach inside; 0 omits it
        # One smaller, brighter fixture straight over the turntable centre: a tighter source than
        # the broad panels, so the model on the turntable gets a readable contact shadow.
        "key": {"w": 100.0, "l": 220.0, "intensity": 700000.0},
    },
    # Cove strips along the side walls, washing the acoustic panels from above.
    "strips": {"z": 960.0, "y": (-1450.0, 1450.0), "off": 18.0, "w": 10.0, "intensity": 4000.0},
}

# emissiveColor 1.0 on a UsdPreviewSurface lights a floor about as much as a RectLight of intensity
# 170 of the same size (measured with ovrtx 0.6 PathTracing, 2026-10-26). Emitter surfaces use
# intensity / EMIT_PER_UNIT so a fixture's visible face matches the RectLight behind it.
EMIT_PER_UNIT = 170.0

# Materials: diffuse, roughness, metallic, plus optional procedural texture set or emission.
MATERIALS = {
    "HallFloor": {"tex": "concrete"},
    "TestFloor": {"tex": "epoxy"},
    "Turntable": {"tex": "turntable"},
    "Belt": {"tex": "belt"},
    "Acoustic": {"tex": "perf"},
    "Honeycomb": {"tex": "honeycomb"},
    "Shell": {"color": (0.78, 0.78, 0.76), "rough": 0.24},       # white gloss paint on the skin
    "ShellRib": {"color": (0.46, 0.47, 0.48), "rough": 0.42},    # light-grey painted steel ribs, flanges
    "Seam": {"color": (0.10, 0.10, 0.105), "rough": 0.65},       # sealed panel joints
    "ShellTrim": {"color": (0.36, 0.36, 0.37), "rough": 0.35},
    "Steel": {"color": (0.20, 0.20, 0.21), "rough": 0.45},
    "SettlingDark": {"color": (0.06, 0.06, 0.065), "rough": 0.55},
    "Gap": {"color": (0.008, 0.008, 0.008), "rough": 0.9},
    "Metal": {"color": (0.62, 0.62, 0.63), "rough": 0.28, "metal": 1.0},
    "Accent": {"color": (0.90, 0.38, 0.06), "rough": 0.45},   # safety orange, the one accent
    "EmitPool": {"emit": CFG["lights"]["pool_intensity"]},
    "EmitHall": {"emit": CFG["lights"]["intensity"]},
    "EmitKey": {"emit": CFG["lights"]["key"]["intensity"]},
    "EmitStrip": {"emit": CFG["strips"]["intensity"]},
}


# ---------------------------------------------------------------------------------------------
# Procedural textures computed in Warp and written through nvImageCodec.
# Spectral noise is periodic, so each map repeats seamlessly.
# ---------------------------------------------------------------------------------------------
def tex_perf(n=1024, tile=40.0, pitch=4.0, hole_r=0.8, depth=0.15, edge=0.1, seed=11):
    from texture_compute import material_maps
    material_maps(TEX_DIR, "perf", 0, n, [tile, tile, pitch, hole_r, depth, edge], (2.0,), seed)
    return tile


def tex_honeycomb(n=1024, s=4.0, kx=4, kz=7, wall=0.5):
    from texture_compute import material_maps
    tx, tz = 3 * s * kx, math.sqrt(3) * s * kz
    material_maps(TEX_DIR, "honeycomb", 1, n, [tx, tz, s, wall])
    return tx, tz


def tex_floor(name, n, tile, base, mottle, grain, rough, rough_var, seam_w, seed):
    from texture_compute import material_maps
    material_maps(TEX_DIR, name, 2, n, [tile, tile, base, mottle, grain, rough, rough_var, seam_w],
                  (3.2, 2.2, 0.6, 1.6), seed)
    return tile


def tex_belt(n=512, tile=20.0, grooves=10, seed=41):
    from texture_compute import material_maps
    material_maps(TEX_DIR, "belt", 3, n, [tile, tile, grooves], (1.0,), seed)
    return tile


def make_textures():
    """Writes every texture set; returns the tile sizes (cm per repeat) the UVs need."""
    hc = CFG["honeycomb"]
    return {
        "perf": tex_perf(),
        "honeycomb": tex_honeycomb(s=hc["cell_side"], wall=hc["cell_wall"]),
        "concrete": tex_floor("concrete", 2048, 600.0, 0.12, 0.16, 0.05, 0.50, 0.12, 1.2, 21),
        "epoxy": tex_floor("epoxy", 2048, 400.0, 0.18, 0.05, 0.015, 0.30, 0.06, 0.8, 31),
        "turntable": tex_floor("turntable", 1024, 300.0, 0.22, 0.03, 0.01, 0.26, 0.05, 0.0, 51),
        "belt": tex_belt(),
    }


# ---------------------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------------------
def smooth5(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (10 - 15 * x + 6 * x * x)


def nozzle_size(y):
    n = CFG["nozzle"]
    s = smooth5((y - n["exit_y"]) / (n["inlet_y"] - n["exit_y"]))
    lerp = lambda a, b: a + (b - a) * s  # noqa: E731
    return lerp(n["exit_hw"], n["inlet_hw"]), lerp(n["exit_h"], n["inlet_h"]), lerp(n["exit_r"], n["inlet_r"])


def ring(y, hw, h, r, off, n_arc):
    p = ml.u_profile(hw + off, h + off, r + off, n_arc)
    return np.stack([p[:, 0], np.full(len(p), y), p[:, 1]], 1)


def nozzle_mesh():
    """One continuous shell: outer skin inlet->exit, half-round lip, inner skin exit->inlet."""
    n = CFG["nozzle"]
    t, na = n["wall"], n["n_arc"]
    ys = np.linspace(n["inlet_y"], n["exit_y"], n["stations"])
    rings = [ring(y, *nozzle_size(y), t, na) for y in ys]
    hw, h, r = nozzle_size(n["exit_y"])
    for i in range(1, n["lip_steps"]):
        th = math.pi * i / n["lip_steps"]
        rings.append(ring(n["exit_y"] - 0.5 * t * math.sin(th), hw, h, r, 0.5 * t * (1 + math.cos(th)), na))
    first_inner = len(rings)
    rings += [ring(y, *nozzle_size(y), 0.0, na) for y in ys[::-1]]
    pts, faces = ml.loft(rings, closed=False)
    k = len(rings[0])
    probe = first_inner * (k - 1) + (k - 1) // 2  # inner skin, top centre, at the exit
    return pts, ml.orient_outward(pts, faces, probe, (0, 0, -1))


def collector_mesh():
    """Bell mouth: outer skin, rolled lip facing upstream, then a gently opening diffuser."""
    c = CFG["collector"]
    hw, h, r, R, na = c["throat_hw"], c["throat_h"], c["throat_r"], c["lip_r"], c["n_arc"]
    yt = c["lip_y"] - R
    rings = [ring(y, hw, h, r, 2 * R, na) for y in np.linspace(c["end_y"], yt, c["stations"])]
    for i in range(1, c["roll_steps"]):
        ph = math.pi * (1 - i / c["roll_steps"])
        rings.append(ring(yt + R * math.sin(ph), hw, h, r, R * (1 - math.cos(ph)), na))
    first_inner = len(rings)
    tan_a = math.tan(math.radians(c["diffuser_deg"]))
    rings += [ring(y, hw, h, r, (yt - y) * tan_a, na) for y in np.linspace(yt, c["end_y"], c["stations"])]
    pts, faces = ml.loft(rings, closed=False)
    k = len(rings[0])
    probe = first_inner * (k - 1) + (k - 1) // 2
    return pts, ml.orient_outward(pts, faces, probe, (0, 0, -1))


def u_path(y, hw, h, r, n_arc=24):
    """The U profile as a 3D polyline in the plane at y (left foot, over the top, right foot)."""
    p = ml.u_profile(hw, h, r, n_arc)
    return np.stack([p[:, 0], np.full(len(p), y), p[:, 1]], 1)


def honeycomb_mesh(tile):
    """The honeycomb face as one planar polygon facing downstream, with UVs in the hex lattice's
    own period (tile = (tx, tz) cm)."""
    y = CFG["honeycomb"]["y"]
    p = ml.u_profile(*nozzle_size(y), CFG["nozzle"]["n_arc"])
    pts = np.stack([p[:, 0], np.full(len(p), y), p[:, 1]], 1)
    face = list(range(len(pts)))
    # Face downstream (-Y) so it reads through the exit.
    if ml.newell(pts[face]) @ np.array([0, -1.0, 0]) < 0:
        face.reverse()
    uv = np.stack([pts[face, 0] / tile[0], pts[face, 2] / tile[1]], 1)
    return pts, [face], uv


def honeycomb_frame():
    """Perimeter frame inside the contraction wall plus a grid of mullions, standing just
    downstream of the honeycomb face: the panel frames that hold the honeycomb modules."""
    hc = CFG["honeycomb"]
    y = hc["y"]
    hw, h, r = nozzle_size(y)
    fw, fd, mw = hc["frame_w"], hc["frame_d"], hc["mullion_w"]
    parts = [ml.sweep(u_path(y, hw, h, r), ml.rect_section(-fw, 1.0, -fd, 0.0), (0, 1, 0))]
    straight = hw - r
    nx = hc["bays_x"]
    for i in range(1, nx):
        x = -hw + 2 * hw * i / nx
        if abs(x) + mw / 2 > straight:
            continue
        parts.append(ml.chamfered_box((x - mw / 2, y - fd + 2, 0.0), (x + mw / 2, y, h - fw + 1), 0.8))
    for j in range(1, hc["bays_z"]):
        z = h * j / hc["bays_z"]
        parts.append(ml.chamfered_box((-hw + fw - 1, y - fd + 2, z - mw / 2), (hw - fw + 1, y, z + mw / 2), 0.8))
    return parts


def flange_bolts(path, axis, hardware):
    """Matching washer and chamfered hex-head geometry along a flange centreline."""
    pitch = hardware["bolt_pitch"]
    points, _ = ml.resample(path, pitch, margin=pitch * 0.6)
    direction = np.asarray(axis, float)
    direction /= np.linalg.norm(direction)
    bolts = []
    for i, point in enumerate(points):
        bolts.append(ml.ngon_prism(point, direction, hardware["washer_r"], hardware["washer_h"], n=16))
        head = point + direction * hardware["washer_h"]
        bolts.append(ml.ngon_prism(head, direction, hardware["bolt_r"], hardware["bolt_h"],
                                   n=6, spin=0.37 * i, chamfer=0.3))
    return bolts


def nozzle_hardware():
    """Exit flange with bolt heads, stiffener ribs and seam grooves on the outer skin."""
    n, fl = CFG["nozzle"], CFG["flange"]
    t = n["wall"]
    hw, h, r = nozzle_size(n["exit_y"])
    y0 = n["exit_y"] + 1.0
    path = u_path(y0, hw, h, r)
    flange = [ml.sweep(path, ml.rect_section(t - 2.0, t + fl["width"], 0.0, fl["thick"]), (0, 1, 0))]
    # Bolts on the downstream face of the flange, along the bolt circle.
    bolt_path = u_path(y0, hw + t + fl["bolt_offset"], h + t + fl["bolt_offset"], r + t + fl["bolt_offset"])
    bolts = flange_bolts(bolt_path, (0, -1, 0), fl)
    rb, sm = CFG["nozzle_ribs"], CFG["nozzle_seams"]
    ribs = [ml.sweep(u_path(y, *nozzle_size(y)), ml.rect_section(t - 3.0, t + rb["height"], -rb["half_w"], rb["half_w"]),
                     (0, 1, 0)) for y in rb["y"]]
    seams = [shell_band(y, sm["half_w"], t - sm["embed"], t + sm["proud"]) for y in sm["y"]]
    seams += nozzle_long_seams()
    return flange, bolts, ribs, seams


def shell_band(y, a, off_lo, off_hi):
    """A circumferential band on the nozzle skin from y - a to y + a, between the offsets off_lo
    and off_hi from the inner profile. Each edge follows the skin at its own station, so the band
    hugs the contraction's slope instead of cutting into it like a flat ring would."""
    na = CFG["nozzle"]["n_arc"]
    rs = [ring(y - a, *nozzle_size(y - a), off_lo, na), ring(y - a, *nozzle_size(y - a), off_hi, na),
          ring(y + a, *nozzle_size(y + a), off_hi, na), ring(y + a, *nozzle_size(y + a), off_lo, na)]
    k = len(rs[0])
    pts = np.vstack(rs)
    sides = [[i * k + j, i * k + j + 1, ((i + 1) % 4) * k + j + 1, ((i + 1) % 4) * k + j]
             for i in range(4) for j in range(k - 1)]
    caps = []
    for c in ([0, k, 2 * k, 3 * k], [k - 1, 2 * k - 1, 3 * k - 1, 4 * k - 1]):
        caps.append(c if ml.newell(pts[c])[2] < 0 else c[::-1])  # both feet face the floor (-Z)
    flipped = [f[::-1] for f in sides]
    if ml.signed_volume(pts, flipped + caps) > ml.signed_volume(pts, sides + caps):
        sides = flipped
    return pts, sides + caps


def nozzle_long_seams():
    """Longitudinal panel seams on the nozzle skin, exit flange to inlet: the four corner tangent
    lines, both sides at mid-height and the roof centre. Each is a thin strip lofted through the
    contraction, its section laid in the station's own (x, z) plane."""
    n, sm = CFG["nozzle"], CFG["nozzle_seams"]
    t, a = n["wall"], sm["half_w"]
    lo, hi = -sm["embed"], sm["proud"]

    def frame(y, which, s):
        hw, h, r = nozzle_size(y)
        if which == "side_mid":
            return (s * (hw + t), 0.5 * h), (s, 0.0), (0.0, 1.0)
        if which == "tan_side":
            return (s * (hw + t), h - r), (s, 0.0), (0.0, 1.0)
        if which == "tan_top":
            return (s * (hw - r), h + t), (0.0, 1.0), (1.0, 0.0)
        return (0.0, h + t), (0.0, 1.0), (1.0, 0.0)  # roof centre

    out = []
    ys = np.linspace(*sm["long_y"], sm["stations"])
    lines = [(w, s) for w in ("side_mid", "tan_side", "tan_top") for s in (-1, 1)] + [("top", 1)]
    for which, s in lines:
        rings = []
        for y in ys:
            (px, pz), (nx, nz), (ex, ez) = frame(y, which, s)
            rings.append(np.array([(px + nx * dn + ex * de, y, pz + nz * dn + ez * de)
                                   for dn, de in ((lo, -a), (hi, -a), (hi, a), (lo, a))]))
        out.append(ml.tube(rings))
    return out


def member(p0, p1, w, ext=None):
    """A straight square steel tube (chamfered corners) from p0 to p1, run on past both ends by
    ext so joints overlap rather than meet face to face (the validator's weld check flags points
    that coincide)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    T = (p1 - p0) / np.linalg.norm(p1 - p0)
    ext = 0.3 * w if ext is None else ext
    B = np.cross(T, (0.0, 0.0, 1.0))
    B = np.array([1.0, 0.0, 0.0]) if np.linalg.norm(B) < 1e-3 else B / np.linalg.norm(B)
    h, c = w / 2, 0.12 * w
    sec = np.array([(h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c),
                    (-h + c, -h), (h - c, -h)])
    return ml.sweep([p0 - T * ext, p1 + T * ext], sec, B)


def side_supports(stations, skin, rib):
    """Splayed A-frame supports along both sides of a duct. skin(y) -> (outer half-width, outer
    top) at station y; rib: how far the bearing rib stands proud of the skin. Per station and
    side: a vertical post bearing on the rib, a raker splayed out to a floor anchor and meeting
    the post high up, a low tie between them, and base plates. Between consecutive stations: an
    X-brace between the posts and a strut linking the apexes."""
    S = CFG["supports"]
    m = S["member"]
    pw, pt = S["plate"]
    out, posts = [], {-1: [], 1: []}
    for y in stations:
        xo, top = skin(y)
        za, zt = S["apex"] * top, S["tie"] * top
        for s in (-1, 1):
            xp = s * (xo + rib + m / 2 - 2.0)
            xf = s * (xo + S["spread"] * top)
            out.append(member((xp, y, 0.0), (xp, y, za + 0.6 * m), m))
            out.append(member((xf, y, 0.0), (xp, y, za), m))
            xr = xf + (xp - xf) * zt / za  # raker x at the tie height
            out.append(member((xp, y, zt), (xr, y, zt), 0.8 * m))
            for x in (xp, xf):
                out.append(ml.chamfered_box((x - pw / 2, y - pw / 2, -0.5), (x + pw / 2, y + pw / 2, pt), 0.6))
            posts[s].append((xp, y, za, top))
    for s in (-1, 1):
        for (x0, y0, a0, t0), (x1, y1, a1, t1) in zip(posts[s], posts[s][1:]):
            lo0, lo1 = 0.08 * t0, 0.08 * t1
            out.append(member((x0, y0, lo0), (x1, y1, a1 * 0.92), 0.7 * m))
            out.append(member((x0, y0, a0 * 0.92), (x1, y1, lo1), 0.7 * m))
            out.append(member((x0, y0, a0), (x1, y1, a1), 0.8 * m))
    return out


def chamber_portal():
    """One heavy portal around the settling chamber, just upstream of the contraction inlet:
    two box columns on base plates, a deep header, and an outside raking brace per column."""
    P, n = CFG["chamber_portal"], CFG["nozzle"]
    ihw, ih, _ = nozzle_size(n["inlet_y"])
    m = n["wall"] + n["settling_margin"]
    xo, zt = ihw + m + 4.0, ih + m + 4.0
    c, d, hd, y = P["col"], P["depth"], P["header"], P["y"]
    out = []
    for s in (-1, 1):
        x0, x1 = sorted((s * xo, s * (xo + c)))
        out.append(ml.chamfered_box((x0, y - d / 2, 0.0), (x1, y + d / 2, zt + hd - 4.0), 2.0))
        out.append(ml.chamfered_box((x0 - 15, y - d / 2 - 15, -0.5), (x1 + 15, y + d / 2 + 15, 4.0), 1.0))
        xc = s * (xo + c)
        foot = xc + s * P["knee"]
        out.append(member((foot, y, 0.0), (xc - s * 10.0, y, 0.55 * zt), 26.0))
        out.append(ml.chamfered_box((foot - 30, y - 30, -0.5), (foot + 30, y + 30, 3.0), 0.6))
    out.append(ml.chamfered_box((-xo - c - 6.0, y - d / 2 - 2.0, zt), (xo + c + 6.0, y + d / 2 + 2.0, zt + hd), 2.0))
    return out


def panel_grid(mb, axis, plane, outward, u_rng, v_rng, skip=None, tile=None):
    """Acoustic panels on a wall. axis: the wall normal axis (0 x, 1 y, 2 z); plane: the interior
    face coordinate; outward: +1/-1, the direction INTO the hall from the wall."""
    hcfg = CFG["hall"]
    g, d, ch = hcfg["panel_gap"], hcfg["panel_depth"], hcfg["panel_chamfer"]
    others = [a for a in range(3) if a != axis]
    nu = max(1, round((u_rng[1] - u_rng[0]) / hcfg["panel"]))
    nv = max(1, round((v_rng[1] - v_rng[0]) / hcfg["panel"]))
    pu, pv = (u_rng[1] - u_rng[0]) / nu, (v_rng[1] - v_rng[0]) / nv
    for i in range(nu):
        for j in range(nv):
            u0, u1 = u_rng[0] + i * pu + g / 2, u_rng[0] + (i + 1) * pu - g / 2
            v0, v1 = v_rng[0] + j * pv + g / 2, v_rng[0] + (j + 1) * pv - g / 2
            if skip and skip(u0, u1, v0, v1):
                continue
            lo, hi = [0.0] * 3, [0.0] * 3
            lo[others[0]], hi[others[0]] = u0, u1
            lo[others[1]], hi[others[1]] = v0, v1
            a, b = plane, plane + outward * d
            lo[axis], hi[axis] = min(a, b), max(a, b)
            mb.add(*ml.chamfered_box(lo, hi, ch), tile=tile)


def build_parts(tiles):
    """Returns {group: {name: (MeshBuilder, material)}}."""
    H, F = CFG["hall"], CFG["floor"]
    (x0, x1), (y0, y1), (z0, z1) = H["x"], H["y"], H["z"]
    wt = H["wall_t"]
    parts = {"Floor": {}, "Tunnel": {}, "Hall": {}}

    def part(group, name, mat, *geoms, crease=35.0, tile=None, origin=(0.0, 0.0, 0.0)):
        mb = ml.MeshBuilder()
        for pts, faces in geoms:
            uv = None if tile is None else ml.box_uv(pts, faces, tile, origin)
            mb.add(pts, faces, crease, uv=uv)
        parts[group][name] = (mb, mat)

    # Floor: slab, test-section inset, turntable with seams, rolling road, centreline.
    part("Floor", "Slab", "HallFloor", ml.chamfered_box((x0, y0, -F["thick"]), (x1, y1, 0.0), F["chamfer"]),
         tile=tiles["concrete"], origin=(-1500.0, -1600.0, 0.0))
    tf = CFG["test_floor"]
    part("Floor", "TestFloor", "TestFloor",
         ml.chamfered_box((tf["x"][0], tf["y"][0], tf["bottom"]), (tf["x"][1], tf["y"][1], tf["top"]), 0.2),
         tile=tiles["epoxy"], origin=(-200.0, 700.0, 0.0))
    tt = CFG["turntable"]
    cx, cy, R = tt["cx"], tt["cy"], tt["r"]
    part("Floor", "Turntable", "Turntable", ml.disc(cx, cy, tt["top"], tt["bottom"], R - tt["ring_w"]),
         tile=tiles["turntable"], origin=(cx, cy, 0.0))
    part("Floor", "TurntableRing", "Metal", ml.annulus(cx, cy, tt["ring_top"], tt["bottom"], R - tt["ring_w"], R))
    sw = tt["seam_w"]
    part("Floor", "TurntableSeams", "Gap",
         ml.annulus(cx, cy, 0.08, -1.0, R, R + sw),
         ml.annulus(cx, cy, 0.12, -1.0, R - tt["ring_w"] - sw, R - tt["ring_w"]))
    b = CFG["belt"]
    hx, hy, g = b["hw"], b["half_len"], b["gap"]
    part("Floor", "RollingRoadBelt", "Belt",
         ml.chamfered_box((-hx + g, cy - hy, b["bottom"]), (hx - g, cy + hy, b["top"]), 0.3),
         tile=tiles["belt"])
    dg, ep, fw, ft = b["drum_gap"], b["end_plate"], b["frame_w"], b["frame_top"]
    part("Floor", "RollingRoadSlot", "Gap",
         ml.chamfered_box((-hx, cy - hy - dg, -4.0), (hx, cy + hy + dg, 0.12), 0.1))
    part("Floor", "RollingRoadDrums", "Metal",
         *[ml.ngon_prism((-hx + g, cy + s * (hy + dg / 2), b["top"] - 0.1 - b["drum_r"]), (1, 0, 0),
                         b["drum_r"], 2 * (hx - g), n=24) for s in (-1, 1)], crease=40.0)
    plates = [ml.chamfered_box((-hx - fw, cy - hy - dg - ep, b["bottom"]), (-hx, cy + hy + dg + ep, ft), 0.2),
              ml.chamfered_box((hx, cy - hy - dg - ep, b["bottom"]), (hx + fw, cy + hy + dg + ep, ft), 0.2)]
    for s in (-1, 1):  # end plates tuck half a width into the side plates so no points coincide
        ya, yb = sorted((cy + s * (hy + dg), cy + s * (hy + dg + ep)))
        plates.append(ml.chamfered_box((-hx - fw / 2, ya, b["bottom"]), (hx + fw / 2, yb, ft), 0.2))
    part("Floor", "RollingRoadPlates", "Metal", *plates)
    wb = CFG["wheel_belts"]
    belts, slots, frames = [], [], []
    for wx, wy in wb["units"]:
        bw, bl, wg, wf = wb["w"] / 2, wb["l"] / 2, wb["gap"], wb["frame_w"]
        belts.append(ml.chamfered_box((wx - bw, wy - bl, wb["bottom"]), (wx + bw, wy + bl, wb["top"]), 0.3))
        slots.append(ml.chamfered_box((wx - bw - wg, wy - bl - wg, wb["bottom"] - 1.0),
                                      (wx + bw + wg, wy + bl + wg, wb["slot_top"]), 0.1))
        ox, oy = bw + wg, bl + wg   # inner edge of the frame
        for s in (-1, 1):           # side rails full length, end rails tucked half a width into them
            xa, xb = sorted((wx + s * ox, wx + s * (ox + wf)))
            frames.append(ml.chamfered_box((xa, wy - oy - wf, wb["bottom"]), (xb, wy + oy + wf, wb["frame_top"]), 0.2))
            ya, yb = sorted((wy + s * oy, wy + s * (oy + wf)))
            frames.append(ml.chamfered_box((wx - ox - wf / 2, ya, wb["bottom"]), (wx + ox + wf / 2, yb, wb["frame_top"]),
                                           0.2))
    part("Floor", "WheelBelts", "Belt", *belts, tile=tiles["belt"])
    part("Floor", "WheelBeltSlots", "Gap", *slots)
    part("Floor", "WheelBeltFrames", "Metal", *frames)
    c = CFG["centreline"]
    tt_edge = R + sw + c["turntable_clear"]
    part("Floor", "Centreline", "Accent",
         ml.chamfered_box((-c["hw"], c["y"][0], -1.0), (c["hw"], cy - tt_edge, c["top"]), 0.1),
         ml.chamfered_box((-c["hw"], cy + tt_edge, -1.0), (c["hw"], c["y"][1], c["top"]), 0.1))

    # Tunnel hardware.
    n = CFG["nozzle"]
    t = n["wall"]
    part("Tunnel", "Nozzle", "Shell", nozzle_mesh(), crease=40.0)
    flange, bolts, ribs, seams = nozzle_hardware()
    part("Tunnel", "NozzleFlange", "ShellRib", *flange, *ribs, crease=40.0)
    part("Tunnel", "NozzleBolts", "Metal", *bolts, crease=40.0)
    part("Tunnel", "NozzleSeams", "Seam", *seams, crease=40.0)

    def nozzle_skin(y):
        hw, h, _ = nozzle_size(y)
        return hw + t, h + t

    part("Tunnel", "NozzleSupports", "Steel",
         *side_supports(CFG["supports"]["y"], nozzle_skin, CFG["nozzle_ribs"]["height"]))
    part("Tunnel", "ChamberPortal", "Steel", *chamber_portal())
    ihw, ih, _ = nozzle_size(n["inlet_y"])
    m = n["wall"] + n["settling_margin"]
    part("Tunnel", "SettlingChamber", "SettlingDark",
         ml.chamfered_box((-ihw - m, n["inlet_y"] - 10.0, 0.0), (ihw + m, y1, ih + m), 4.0))
    hpts, hfaces, huv = honeycomb_mesh(tiles["honeycomb"])
    mb = ml.MeshBuilder().add(hpts, hfaces, uv=huv)
    parts["Tunnel"]["Honeycomb"] = (mb, "Honeycomb")
    part("Tunnel", "HoneycombFrame", "ShellTrim", *honeycomb_frame(), crease=40.0)
    part("Tunnel", "Collector", "Shell", collector_mesh(), crease=40.0)
    cc = CFG["collector"]
    R = cc["lip_r"]
    part("Tunnel", "CollectorTrim", "Metal",
         ml.sweep(u_path(cc["lip_y"] + 0.5, cc["throat_hw"] + R, cc["throat_h"] + R, cc["throat_r"] + R, 32),
                  ml.circle_section(cc["trim_r"], 12), (0, 1, 0)), crease=60.0)
    # Collector outer skin is constant: the throat profile offset by 2 x lip radius.
    ohw, oh, orr = cc["throat_hw"] + 2 * R, cc["throat_h"] + 2 * R, cc["throat_r"] + 2 * R
    rings = [ml.sweep(u_path(cc["flange_y"], ohw, oh, orr), ml.rect_section(-3.0, 18.0, -5.0, 5.0), (0, 1, 0))]
    rings += [ml.sweep(u_path(y, ohw, oh, orr), ml.rect_section(-3.0, 11.0, -5.0, 5.0), (0, 1, 0))
              for y in cc["ribs_y"]]
    part("Tunnel", "CollectorRibs", "ShellRib", *rings, crease=40.0)
    part("Tunnel", "CollectorSupports", "Steel",
         *side_supports(CFG["collector_supports"]["y"], lambda y: (ohw, oh), 11.0))
    # Bulkhead frame: a flat plate ring standing out from the outer skin just behind the roll, so
    # the bell mouth reads as set into a structure rather than as a free-standing tube.
    part("Tunnel", "CollectorFace", "ShellRib",
         ml.sweep(u_path(cc["face_y"], ohw, oh, orr), ml.rect_section(-3.0, cc["face_w"], -cc["face_t"] / 2,
                                                                      cc["face_t"] / 2), (0, 1, 0)), crease=40.0)
    # The collector shares the nozzle's fastener style, spaced along its bulkhead centreline.
    bolt_offset = cc["face_w"] / 2
    bolt_path = u_path(cc["face_y"] + cc["face_t"] / 2, ohw + bolt_offset,
                       oh + bolt_offset, orr + bolt_offset)
    hardware = dict(CFG["flange"], bolt_pitch=cc["face_bolt_pitch"])
    part("Tunnel", "CollectorFasteners", "Metal", *flange_bolts(bolt_path, (0, 1, 0), hardware))
    # Safety screen across the diffuser end: a dark backing face and a grid of bars before it.
    ys = cc["screen_y"]
    off = (cc["lip_y"] - R - ys) * math.tan(math.radians(cc["diffuser_deg"]))
    shw, sh_, sr = cc["throat_hw"] + off, cc["throat_h"] + off, cc["throat_r"] + off
    sp = ml.u_profile(shw, sh_, sr, cc["n_arc"])
    spts = np.stack([sp[:, 0], np.full(len(sp), ys), sp[:, 1]], 1)
    sface = list(range(len(spts)))
    if ml.newell(spts[sface]) @ np.array([0, 1.0, 0]) < 0:
        sface.reverse()
    part("Tunnel", "CollectorScreenBacking", "Gap", (spts, [sface]))
    pitch, bw = cc["screen_pitch"], cc["screen_bar"]
    yb = (ys + 2.0, ys + 6.0)

    def top_at(x):
        e = abs(x) - (shw - sr)
        return sh_ if e <= 0 else sh_ - sr + math.sqrt(max(sr * sr - e * e, 0.0))

    def half_at(z):
        e = z - (sh_ - sr)
        return shw if e <= 0 else shw - sr + math.sqrt(max(sr * sr - e * e, 0.0))

    bars = []
    nx = int((2 * shw) // pitch)
    for i in range(1, nx + 1):
        x = -shw + i * (2 * shw) / (nx + 1)
        bars.append(ml.chamfered_box((x - bw / 2, yb[0], 0.0), (x + bw / 2, yb[1], top_at(x) - 1.5), 0.6))
    nz = int(sh_ // pitch)
    for j in range(1, nz + 1):
        z = j * sh_ / (nz + 1)
        hx = half_at(z) - 1.5
        bars.append(ml.chamfered_box((-hx, yb[0] + 0.7, z - bw / 2), (hx, yb[1] - 0.7, z + bw / 2), 0.6))
    part("Tunnel", "CollectorScreen", "Steel", *bars)

    # Plenum hall: per wall, a dark backing slab outside the interior (it shows in the panel
    # seams) and charcoal perforated acoustic panels standing proud of it. Kept per wall so each
    # prim's bounds stay tight.
    walls = {
        "WallLeft": ((x0 - wt, y0 - wt, z0), (x0, y1 + wt, z1), (0, x0, +1, (y0, y1), (z0, z1), None)),
        "WallRight": ((x1, y0 - wt, z0), (x1 + wt, y1 + wt, z1), (0, x1, -1, (y0, y1), (z0, z1), None)),
        # The collector diffuser runs into this wall, and the panels behind it are hidden by the
        # duct and its screen; skipping whole 300 cm panels left a black void around the collector.
        "WallDownstream": ((x0, y0 - wt, z0), (x1, y0, z1), (1, y0, +1, (x0, x1), (z0, z1), None)),
        # The settling chamber box runs into this wall and hides the panels behind it; skipping
        # whole 300 cm panels here instead left a black void around the chamber.
        "WallUpstream": ((x0, y1, z0), (x1, y1 + wt, z1), (1, y1, -1, (x0, x1), (z0, z1), None)),
        "Ceiling": ((x0 - wt, y0 - wt, z1), (x1 + wt, y1 + wt, z1 + wt), (2, z1, -1, (x0, x1), (y0, y1), None)),
    }
    for name, (lo, hi, (axis, plane, sign, ur, vr, skip)) in walls.items():
        parts["Hall"][name + "Backing"] = (ml.MeshBuilder().add(*ml.chamfered_box(lo, hi, 2.0)), "Gap")
        mb = ml.MeshBuilder()
        panel_grid(mb, axis, plane, sign, ur, vr, skip, tile=tiles["perf"])
        parts["Hall"][name] = (mb, "Acoustic")

    # Ceiling fixtures: a steel housing per light with an emissive diffuser on its underside.
    L = CFG["lights"]
    za, zb = L["panel_z"]
    housing, diff = {"EmitPool": [], "EmitHall": []}, {"EmitPool": [], "EmitHall": []}
    for x, y, pool in light_grid():
        k = "EmitPool" if pool else "EmitHall"
        e = L["housing"]
        housing[k].append(ml.chamfered_box((x - L["w"] / 2 - e, y - L["l"] / 2 - e, za), (x + L["w"] / 2 + e, y + L["l"] / 2 + e, zb), 1.0))
        diff[k].append(ml.chamfered_box((x - L["w"] / 2, y - L["l"] / 2, za - 0.6), (x + L["w"] / 2, y + L["l"] / 2, za + 0.2), 0.2))
    kx, ky, K = 0.0, CFG["turntable"]["cy"], L["key"]
    e = L["housing"]
    housing["EmitPool"].append(ml.chamfered_box((kx - K["w"] / 2 - e, ky - K["l"] / 2 - e, za),
                                                (kx + K["w"] / 2 + e, ky + K["l"] / 2 + e, zb), 1.0))
    part("Hall", "LightDiffuserKey", "EmitKey",
         ml.chamfered_box((kx - K["w"] / 2, ky - K["l"] / 2, za - 0.6), (kx + K["w"] / 2, ky + K["l"] / 2, za + 0.2), 0.2))
    part("Hall", "LightHousings", "Steel", *(housing["EmitPool"] + housing["EmitHall"]))
    for k, name in (("EmitPool", "LightDiffusersPool"), ("EmitHall", "LightDiffusersHall")):
        if diff[k]:
            part("Hall", name, k, *diff[k])
    S = CFG["strips"]
    strips = []
    for s in (-1, 1):
        xw = s * (x1 - H["panel_depth"])
        xa, xb = sorted((xw, xw - s * S["off"]))
        strips.append(ml.chamfered_box((xa, S["y"][0], S["z"]), (xb, S["y"][1], S["z"] + 4.0), 0.5))
    part("Hall", "CoveStrips", "EmitStrip", *strips)
    return parts


def light_grid():
    """(x, y, is_pool) for every ceiling fixture."""
    L = CFG["lights"]
    return [(x, y, abs(x) <= L["pool"]["x"] and abs(y) <= L["pool"]["y"]) for x in L["rows_x"] for y in L["cols_y"]]


# ---------------------------------------------------------------------------------------------
# Authoring
# ---------------------------------------------------------------------------------------------
def build():
    import usdex.core as ux
    from pxr import Gf, Sdf, UsdGeom, Vt

    # Gf.Rotation() leaves its axis undefined, which intermittently authors NaN matrices.
    IDENTITY_ROT = Gf.Rotation(Gf.Vec3d(0, 0, 1), 0)
    xf = lambda prim, pos, rot=IDENTITY_ROT: ux.setLocalTransform(  # noqa: E731
        prim, Gf.Transform(Gf.Vec3d(*pos), rot, Gf.Vec3d(1, 1, 1)))
    tiles = make_textures()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stage = ux.createStage(str(OUT), "Environment", UsdGeom.Tokens.z, 0.01,
                           "stagewright tools/build_env.py")
    stage.SetTimeCodesPerSecond(60)
    root = ux.defineXform(stage.GetDefaultPrim()).GetPrim()  # Scope -> Xform, identity
    ux.setDisplayName(root, "Open-jet test section")

    looks = ux.defineScope(root, "Looks").GetPrim()
    mats = {}
    for name, spec in MATERIALS.items():
        emit = spec.get("emit")
        col = (0.0, 0.0, 0.0) if emit else spec.get("color", (1.0, 1.0, 1.0))
        mat = ux.definePreviewMaterial(looks, ux.getValidChildName(looks, name), Gf.Vec3f(*col),
                                       roughness=spec.get("rough", 0.5), metallic=spec.get("metal", 0.0))
        if emit:
            k = emit / EMIT_PER_UNIT
            ux.addEmissiveColorToPreviewMaterial(mat, Gf.Vec3f(k, k, k))
        if "tex" in spec:
            rel = f"./textures/{spec['tex']}"
            ok = (ux.addColorTextureToPreviewMaterial(mat, Sdf.AssetPath(f"{rel}_color.png"))
                  and ux.addNormalTextureToPreviewMaterial(mat, Sdf.AssetPath(f"{rel}_normal.png"))
                  and ux.addOrmTextureToPreviewMaterial(mat, Sdf.AssetPath(f"{rel}_orm.png")))
            if not ok:
                raise RuntimeError(f"texture hookup failed for {name}")
        mats[name] = mat

    geo = ux.defineXform(root, "Geometry").GetPrim()
    for group, items in build_parts(tiles).items():
        gprim = ux.defineXform(geo, ux.getValidChildName(geo, group)).GetPrim()
        for name, (mb, mat) in items.items():
            counts, idx, pts, nval, nidx = mb.arrays()
            st = mb.st()
            uvs = None if st is None else ux.Vec2fPrimvarData(
                UsdGeom.Tokens.faceVarying, Vt.Vec2fArray.FromNumpy(st[0]), Vt.IntArray.FromNumpy(st[1]))
            mesh = ux.definePolyMesh(
                gprim, ux.getValidChildName(gprim, name),
                Vt.IntArray.FromNumpy(counts), Vt.IntArray.FromNumpy(idx), Vt.Vec3fArray.FromNumpy(pts),
                normals=ux.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray.FromNumpy(nval),
                                            Vt.IntArray.FromNumpy(nidx)),
                uvs=uvs)
            if not mesh:
                raise RuntimeError(f"definePolyMesh failed for {group}/{name}")
            lo, hi = mb.extent()
            mesh.GetExtentAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*lo.tolist()), Gf.Vec3f(*hi.tolist())]))
            ux.bindMaterial(mesh.GetPrim(), mats[mat])

    L = CFG["lights"]
    lights = ux.defineXform(root, "Lights").GetPrim()
    for k, (x, y, pool) in enumerate(light_grid(), 1):
        light = ux.defineRectLight(lights, f"Panel_{k:02d}", L["w"], L["l"],
                                   L["pool_intensity"] if pool else L["intensity"])
        # RectLight emits along its local -Z: an untransformed light already points down.
        xf(light.GetPrim(), (x, y, L["panel_z"][0] - 0.6 - L["light_gap"]))
    K = L["key"]
    key = ux.defineRectLight(lights, "TurntableKey", K["w"], K["l"], K["intensity"])
    xf(key.GetPrim(), (0.0, CFG["turntable"]["cy"], L["panel_z"][0] - 0.6 - L["light_gap"]))
    S = CFG["strips"]
    for s, side in ((-1, "Left"), (1, "Right")):
        strip = ux.defineRectLight(lights, f"Cove{side}", S["w"], S["y"][1] - S["y"][0], S["intensity"])
        xf(strip.GetPrim(), (s * (CFG["hall"]["x"][1] - CFG["hall"]["panel_depth"] - S["off"] / 2), 0.5 * sum(S["y"]),
                             S["z"] - 0.5))
    if L["dome_intensity"] > 0:
        ux.defineDomeLight(lights, "Fill", L["dome_intensity"])
    # Inside the contraction, just downstream of the honeycomb. Rotating -90 deg about X turns
    # the light's -Z emission to world -Y (downstream) and its local Y (height) to world Z.
    hc = CFG["honeycomb"]
    hw, h, _ = nozzle_size(hc["light_y"])
    fill = ux.defineRectLight(lights, "ContractionFill", 1.8 * hw, 0.9 * h, hc["light_intensity"])
    xf(fill.GetPrim(), (0, hc["light_y"], 0.5 * h), Gf.Rotation(Gf.Vec3d(1, 0, 0), -90))
    # Key on the honeycomb face: high in the contraction, rotated +90 deg about X so it emits
    # upstream (+Y) and grazes the cells from above.
    hw, h, _ = nozzle_size(hc["key_y"])
    key = ux.defineRectLight(lights, "HoneycombKey", 1.6 * hw, 60.0, hc["key_intensity"])
    xf(key.GetPrim(), (0, hc["key_y"], h - 70.0), Gf.Rotation(Gf.Vec3d(1, 0, 0), 90))
    # Dim fill inside the collector throat, emitting downstream (-Y) onto the diffuser walls and
    # the screen, so the intake reads as a receding duct rather than a black hole.
    cc = CFG["collector"]
    cfill = ux.defineRectLight(lights, "CollectorFill", 1.4 * cc["throat_hw"], 0.7 * cc["throat_h"],
                               cc["fill_intensity"])
    xf(cfill.GetPrim(), (0, cc["fill_y"], 0.5 * cc["throat_h"]), Gf.Rotation(Gf.Vec3d(1, 0, 0), -90))

    ux.saveStage(stage, comment="Open-jet test section environment. Generated; do not hand-edit.")
    if re.search(r"\bnan\b", OUT.read_text(encoding="utf-8"), re.IGNORECASE):
        raise RuntimeError(f"NaN authored in {OUT}")
    print("wrote", OUT)


# ---------------------------------------------------------------------------------------------
# Containment check
# ---------------------------------------------------------------------------------------------
def _point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _dist_to_poly(pt, poly):
    p = np.asarray(pt, float)
    best = math.inf
    n = len(poly)
    for i in range(n):
        a, b = np.asarray(poly[i], float), np.asarray(poly[(i + 1) % n], float)
        t = np.clip((p - a) @ (b - a) / max((b - a) @ (b - a), 1e-12), 0, 1)
        best = min(best, float(np.linalg.norm(p - (a + t * (b - a)))))
    return best


def check():
    from pxr import Gf, Usd, UsdGeom

    d = CFG["domain"]
    n, c = CFG["nozzle"], CFG["collector"]
    ok = True
    print("\n== Jet containment (nozzle exit cross-section extruded from exit to collector lip) ==")
    hw, h, r = nozzle_size(n["exit_y"])
    prof = ml.u_profile(hw, h, r, 64)  # open at the floor; close it along z = 0
    poly = [tuple(p) for p in prof]
    worst = math.inf
    for x in d["x"]:
        z = d["z"][1]
        inside = _point_in_poly((x, z), poly)
        dist = _dist_to_poly((x, z), poly)
        worst = min(worst, dist if inside else -dist)
    lip_downstream = n["exit_y"] - 0.5 * n["wall"]
    rows = [
        ("side (each)", hw - d["x"][1]),
        ("top", h - d["z"][1]),
        ("top corners (to rounded exit corner)", worst),
        ("upstream (nozzle exit plane to inlet face)", n["exit_y"] - d["y"][1]),
        ("upstream (lip's most downstream point)", lip_downstream - d["y"][1]),
        ("downstream (outlet face to collector lip)", d["y"][0] - c["lip_y"]),
        ("floor (floor top z=0 to domain bottom)", d["z"][0] - 0.0),
    ]
    for label, v in rows:
        print(f"  {label:48s} {v:8.1f} cm")
        if v <= 0 and not label.startswith("floor"):
            ok = False
    print("  note: the domain bottom (z = -4) sits 4 cm BELOW the floor top (z = 0). The floor is the")
    print("        jet's fourth wall, so this is the blueprint's own ground offset, not a clash.")

    print("\n== Environment geometry vs flow domain (world AABB overlap) ==")
    stage = Usd.Stage.Open(str(OUT))
    root = stage.GetDefaultPrim()
    xf = UsdGeom.XformCache()
    m = xf.GetLocalToWorldTransform(root)
    ident = m == Gf.Matrix4d(1.0)
    ok &= ident
    print(f"  /{root.GetName()} local-to-world is identity: {ident}")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_], useExtentsHint=False)
    lo_d = np.array([d["x"][0], d["y"][0], d["z"][0]])
    hi_d = np.array([d["x"][1], d["y"][1], d["z"][1]])
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Gprim):
            continue
        rng = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        lo, hi = np.array(rng.GetMin()), np.array(rng.GetMax())
        overlap = bool(np.all(lo < hi_d) and np.all(hi > lo_d))
        is_floor = "/Geometry/Floor/" in str(prim.GetPath())
        if overlap and is_floor:
            status = "floor, allowed" if hi[2] <= 0.5 else "FLOOR ITEM TOO HIGH"
            ok &= hi[2] <= 0.5
            print(f"  {str(prim.GetPath()):52s} overlaps domain only below z={hi[2]:.2f}  [{status}]")
        elif overlap:
            ok = False
            print(f"  {str(prim.GetPath()):52s} INTERSECTS the domain  lo={lo.round(1)} hi={hi.round(1)}")
    stage_bound = cache.ComputeWorldBound(root).ComputeAlignedRange()
    print(f"  environment world bound: {np.array(stage_bound.GetMin()).round(1)} .. {np.array(stage_bound.GetMax()).round(1)}")
    print("\nCONTAINMENT", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] != ["check"]:
        build()
    sys.exit(0 if check() else 1)
