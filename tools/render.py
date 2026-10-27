# Render stills from a presentation scene with ovrtx (headless RTX path tracing).
#   python tools/render.py                                   all products, 960x540, 64 spp
#   python tools/render.py --products Hero,Main --spp 256 --res 1920x1080
#   python tools/render.py --scene scenes/present_payload.usda --products Hero
#
# Runs in its own process: it never imports pxr, since ovrtx bundles its own USD runtime.
# Resolution, sample count and the flow-domain ghost's visibility are overridden through a small
# generated USDA layer that sublayers the scene, so the authored scene stays untouched.
# By default the ghost shows only in the blueprint camera's view (Main), and the lighting QC spheres
# are hidden (--qc shows them). --prefix names the outputs, e.g. --prefix final_ for the finals.
# Exit status is 1 if any requested product produced no frame.
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENE = ROOT / "scenes" / "present.usda"
OUT_DIR = ROOT / "build" / "stills"
ALL_PRODUCTS = ("Hero", "Detail", "Main", "Wake")
GHOST_DEFAULT = {"Main"}


def write_override(scene, products, res, spp, ghost, qc, out_dir=OUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(scene, out_dir).replace("\\", "/")
    vis = "inherited" if ghost else "invisible"
    qc_vis = "inherited" if qc else "invisible"
    lines = ["#usda 1.0", "(", f"    subLayers = [@{rel}@]", ")", "",
             'over "World"', "{", '    over "Guides"', "    {", '        over "FlowDomain"', "        {",
             f'            token visibility = "{vis}"', "        }", "    }",
             '    over "Props"', "    {", '        over "QcSpheres"', "        {",
             f'            token visibility = "{qc_vis}"', "        }", "    }", "}", "",
             'over "Render"', "{"]
    for p in products:
        lines += [f'    over "{p}"', "    {"]
        if res:
            lines.append(f"        uniform int2 resolution = ({res[0]}, {res[1]})")
        if spp:
            lines.append(f"        custom uint omni:rtx:pt:samplesPerPixel = {spp}")
        lines.append("    }")
    lines.append("}")
    path = out_dir / f"_override_{scene.stem}_{'ghost' if ghost else 'clean'}.usda"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def render_batch(rtx, scene, products, res, spp, ghost, max_steps, tag, qc, out_dir):
    """Render one group of products that share a ghost setting. Returns the products with no frame."""
    import numpy as np
    from image_io import write_rgb

    import rtx as rt

    layer = write_override(scene, products, res, spp, ghost, qc, out_dir)
    names = {f"/Render/{p}": p for p in products}
    with rt.loaded_scene(rtx, "stills", layer):
        images, status = rt.converge(rtx, names, ordinal=1, delta_time=1 / 30, max_steps=max_steps)
    for path, name in names.items():
        if path not in images:
            print(f"{name}: no frame captured (last status {status.get(path)})")
            continue
        px = images[path]
        progression, converged = status[path]
        rgb = px[..., :3].astype(np.float32)
        luma = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        dst = out_dir / f"{tag}{name.lower()}.png"
        write_rgb(dst, px)
        print(f"{name:7s} ghost={'on ' if ghost else 'off'} progression={progression} "
              f"converged={converged} {px.shape[1]}x{px.shape[0]} mean={luma.mean():.1f} "
              f"black%={(luma < 3).mean() * 100:.1f} clipped%={(rgb.max(axis=-1) >= 254).mean() * 100:.1f}"
              f" -> {dst}")
    return [name for path, name in names.items() if path not in images]


def render(scene, products, res, spp, max_steps, ghost_for, qc=False, prefix="", out_dir=OUT_DIR):
    """Render every product; returns the products that produced no frame."""
    import rtx as rt

    out_dir.mkdir(parents=True, exist_ok=True)
    tag = prefix + ("" if scene.resolve() == DEFAULT_SCENE.resolve() else f"{scene.stem}_")
    batches = [(True, [p for p in products if p in ghost_for]), (False, [p for p in products if p not in ghost_for])]
    missing = []
    with rt.open_renderer() as rtx:
        for ghost, prods in batches:
            if prods:
                missing += render_batch(rtx, scene, prods, res, spp, ghost, max_steps, tag, qc, out_dir)
    return missing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    ap.add_argument("--products", default=",".join(ALL_PRODUCTS))
    ap.add_argument("--res", default="960x540", help="WxH, or 'scene' to keep the authored resolution")
    ap.add_argument("--spp", type=int, default=64, help="0 keeps the authored sample count")
    ap.add_argument("--max-steps", type=int, default=0, help="step cap; default 4 x spp + 64")
    ap.add_argument("--ghost", default="auto", choices=("auto", "on", "off"),
                    help="flow-domain ghost: auto shows it for Main only")
    ap.add_argument("--qc", action="store_true", help="show the lighting QC spheres")
    ap.add_argument("--prefix", default="", help="output file name prefix, e.g. final_")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="output directory (default build/stills)")
    a = ap.parse_args()
    res = None if a.res == "scene" else tuple(int(v) for v in a.res.lower().split("x"))
    products = [p.strip() for p in a.products.split(",") if p.strip()]
    ghost_for = {"auto": GHOST_DEFAULT, "on": set(products), "off": set()}[a.ghost]
    missing = render(a.scene.resolve(), products, res, a.spp, a.max_steps or 4 * max(a.spp, 64) + 64, ghost_for,
                     a.qc, a.prefix, a.out.resolve())
    if missing:
        print(f"FAILED: no frame captured for {', '.join(missing)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
