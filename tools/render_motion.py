# Render the animated Dolly camera frame by frame with ovrtx (headless RTX path tracing).
#   python tools/render_motion.py --frames 0,107,215 --spp 16 --out build/frames/dolly_test
#   python tools/render_motion.py --res 1280x720 --spp 64
#   python tools/render_motion.py --encode          render and encode build/frames/dolly to MP4
#
# Runs in its own process (never imports pxr). Per CLAUDE.md "Camera motion": for each frame the
# stage is repopulated at time frame / fps SECONDS on a new, increasing ordinal, the write floor is
# advanced to it, and the renderer steps that ordinal until the frame converges. Resolution, sample
# count and visibility (no domain ghost, no QC spheres) come from the same generated override layer
# tools/render.py uses.
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as stills  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCENE = ROOT / "scenes" / "present.usda"
FRAMES = ROOT / "build" / "frames" / "dolly"
OUT = ROOT / "build" / "out"
PRODUCT = "Dolly"
FPS = 24
COUNT = 216  # must match DOLLY["frames"] in tools/build_present.py
WARMUP_PASSES = 2


def render(frames, res, spp, out_dir, max_steps):
    import numpy as np
    from image_io import write_rgb

    import rtx as rt

    out_dir.mkdir(parents=True, exist_ok=True)
    layer = stills.write_override(SCENE, [PRODUCT], res, spp, ghost=False, qc=False)
    product = f"/Render/{PRODUCT}"
    # The first frames rendered after the stage loads come out slightly darker than the same
    # frames rendered later (it looks like content still streaming in), which pops at the start
    # of a clip. Render warm-up frames first and discard them: poses just after the first frame,
    # so the same content is in view, and never the first pose itself, since an unchanged camera
    # does not restart the sample accumulation.
    f0 = frames[0]
    warm = [f0 + k if f0 + k < COUNT else f0 - k for k in (3, 2, 1)] * WARMUP_PASSES
    schedule = [(w, False) for w in warm] + [(f, True) for f in frames]
    with rt.open_renderer() as rtx, rt.loaded_scene(rtx, "motion", layer) as scene:
        # Ordinal 1 is the initial load; each scheduled pose gets the next ordinal.
        for ordinal, (f, keep) in enumerate(schedule, start=2):
            rt.seek(scene, ordinal, f / FPS)
            images, status = rt.converge(rtx, [product], ordinal, delta_time=1 / FPS, max_steps=max_steps)
            if product not in images:
                raise RuntimeError(f"frame {f}: no image captured (last status {status.get(product)})")
            if not keep:
                continue
            px = images[product]
            progression, converged = status[product]
            rgb = px[..., :3].astype(np.float32)
            write_rgb(out_dir / f"{f:04d}.png", px)
            print(f"frame {f:4d} ordinal {ordinal:4d} progression={progression} converged={converged} "
                  f"mean={rgb.mean():.1f}", flush=True)


def encode(frames_dir, gif_width, gif_fps, make_gif=False):
    OUT.mkdir(parents=True, exist_ok=True)
    src = str(frames_dir / "%04d.png")
    mp4, gif = OUT / "dolly.mp4", OUT / "dolly.gif"
    from video_io import encode_mp4

    paths = [frames_dir / f"{i:04d}.png" for i in range(COUNT)]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise ValueError(f"Missing dolly frames: {', '.join(missing)}")
    encode_mp4(paths, mp4, FPS)
    print(mp4)
    if not make_gif:
        return
    # The camera moves on every frame, so frame differencing saves little and dithering noise costs a
    # lot. The scene is nearly all grey, so a small undithered palette holds up and keeps the file
    # small enough to embed in a README.
    graph = (f"fps={gif_fps},scale={gif_width}:-1:flags=lanczos,split[a][b];"
             "[a]palettegen=max_colors=64:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", src,
                    "-filter_complex", graph, "-loop", "0", str(gif)], check=True)
    print(gif)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frames", default="all", help="'all' or a comma list of frame numbers")
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--spp", type=int, default=64)
    ap.add_argument("--out", type=Path, default=FRAMES)
    ap.add_argument("--max-steps", type=int, default=0, help="step cap per frame; default 4 x spp + 64")
    ap.add_argument("--encode", action="store_true", help="encode the complete frame sequence in --out to MP4")
    ap.add_argument("--no-render", action="store_true", help="with --encode, skip rendering")
    ap.add_argument("--gif", action="store_true", help="also encode a GIF with ffmpeg (requires --encode)")
    ap.add_argument("--gif-width", type=int, default=640)
    ap.add_argument("--gif-fps", type=int, default=12)
    a = ap.parse_args()
    if (a.gif or a.no_render) and not a.encode:
        ap.error("--gif and --no-render require --encode")
    if not a.no_render:
        frames = list(range(COUNT)) if a.frames == "all" else [int(v) for v in a.frames.split(",")]
        res = tuple(int(v) for v in a.res.lower().split("x"))
        render(frames, res, a.spp, a.out.resolve(), a.max_steps or 4 * max(a.spp, 64) + 64)
    if a.encode:
        encode(a.out.resolve(), a.gif_width, a.gif_fps, a.gif)


if __name__ == "__main__":
    main()
