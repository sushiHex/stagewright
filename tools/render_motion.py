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
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as stills  # noqa: E402
from project_paths import ROOT, SCENES  # noqa: E402

SCENE = SCENES / "present.usda"
FRAMES = ROOT / "build" / "frames" / "dolly"
OUT = ROOT / "build" / "out"
PRODUCT = "Dolly"
FPS = 24
COUNT = 216  # must match DOLLY["frames"] in tools/build_present.py
WARMUP_PASSES = 2


def render(frames, res, spp, out_dir, max_steps, scene=SCENE, product=PRODUCT, fps=FPS, count=COUNT, supersample=2):
    if scene.resolve() != SCENE.resolve() and out_dir.resolve() == FRAMES.resolve():
        raise ValueError("Custom scenes require --out outside the default presentation frame directory")
    import numpy as np
    from image_io import write_rgb

    import rtx as rt

    out_dir.mkdir(parents=True, exist_ok=True)
    render_res = tuple(size * supersample for size in res)
    layer = stills.write_override(scene, [product], render_res, spp, ghost=False, qc=False)
    product = f"/Render/{product}"
    # The first frames rendered after the stage loads come out slightly darker than the same
    # frames rendered later (it looks like content still streaming in), which pops at the start
    # of a clip. Render warm-up frames first and discard them: poses just after the first frame,
    # so the same content is in view, and never the first pose itself, since an unchanged camera
    # does not restart the sample accumulation.
    f0 = frames[0]
    warm = []
    for k in (3, 2, 1):
        if f0 + k < count:
            warm.append(f0 + k)
        elif f0 - k >= 0:
            warm.append(f0 - k)
    warm *= WARMUP_PASSES
    schedule = [(w, False) for w in warm] + [(f, True) for f in frames]
    with rt.open_renderer() as rtx, rt.loaded_scene(rtx, "motion", layer) as loaded:
        # Ordinal 1 is the initial load; each scheduled pose gets the next ordinal.
        for ordinal, (f, keep) in enumerate(schedule, start=2):
            rt.seek(loaded, ordinal, f / fps)
            images, status = rt.converge(rtx, [product], ordinal, delta_time=1 / fps, max_steps=max_steps)
            if product not in images:
                raise RuntimeError(f"frame {f}: no image captured (last status {status.get(product)})")
            if not keep:
                continue
            px = images[product]
            if supersample > 1:
                from image_compute import downsample_rgb
                px = downsample_rgb(px, supersample)
            progression, converged = status[product]
            rgb = px[..., :3].astype(np.float32)
            write_rgb(out_dir / f"{f:04d}.png", px)
            print(f"frame {f:4d} ordinal {ordinal:4d} progression={progression} converged={converged} "
                  f"mean={rgb.mean():.1f}", flush=True)


def encode(frames_dir, gif_width, gif_fps, make_gif=False, fps=FPS, count=COUNT, product=PRODUCT):
    frames_dir = frames_dir.resolve()
    canonical = frames_dir == FRAMES.resolve() and product == PRODUCT and fps == FPS and count == COUNT
    # Only the complete default presentation sequence may replace the public media source.
    # Preview and custom-scene videos stay with their explicitly selected frame directory.
    video_dir = OUT if canonical else frames_dir
    mp4, gif = video_dir / f"{product.lower()}.mp4", video_dir / f"{product.lower()}.gif"
    if not canonical and mp4.resolve() == (OUT / "dolly.mp4").resolve():
        raise ValueError("Choose a frame directory separate from the public video output directory")
    video_dir.mkdir(parents=True, exist_ok=True)
    src = str(frames_dir / "%04d.png")

    paths = [frames_dir / f"{i:04d}.png" for i in range(count)]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise ValueError(f"Missing sequence frames: {', '.join(missing)}")
    from video_io import encode_mp4

    encode_mp4(paths, mp4, fps)
    print(mp4)
    if not make_gif:
        return
    # The camera moves on every frame, so frame differencing saves little and dithering noise costs a
    # lot. The scene is nearly all grey, so a small undithered palette holds up and keeps the file
    # small enough to embed in a README.
    graph = (f"fps={gif_fps},scale={gif_width}:-1:flags=lanczos,split[a][b];"
             "[a]palettegen=max_colors=64:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", src,
                    "-filter_complex", graph, "-loop", "0", str(gif)], check=True)
    print(gif)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", type=Path, default=SCENE,
                    help="presentation USD scene; a custom scene requires a separate --out directory")
    ap.add_argument("--product", default=PRODUCT, help="RenderProduct name under /Render; also names the video")
    ap.add_argument("--fps", type=int, default=FPS, help="sample and playback frame rate")
    ap.add_argument("--count", type=int, default=COUNT, help="number of frames in the complete sequence")
    ap.add_argument("--frames", default="all", help="'all' or a comma list of frame numbers")
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--spp", type=int, default=64)
    ap.add_argument("--supersample", type=int, choices=(1, 2), default=2,
                    help="render scale before Warp filtered downsampling; --res is the output size")
    ap.add_argument("--out", type=Path, default=FRAMES,
                    help="frame directory; custom/preview videos are written here too")
    ap.add_argument("--max-steps", type=int, default=0, help="step cap per frame; default 4 x spp + 64")
    ap.add_argument("--encode", action="store_true", help="encode the complete frame sequence in --out to MP4")
    ap.add_argument("--no-render", action="store_true", help="with --encode, skip rendering")
    ap.add_argument("--gif", action="store_true", help="also encode a GIF with ffmpeg (requires --encode)")
    ap.add_argument("--gif-width", type=int, default=640)
    ap.add_argument("--gif-fps", type=int, default=12)
    a = ap.parse_args(argv)
    if a.scene.resolve() != SCENE.resolve() and a.out.resolve() == FRAMES.resolve():
        ap.error("custom scenes require --out outside the default presentation frame directory")
    if a.out.resolve() == OUT.resolve() and a.product.lower() == "dolly":
        ap.error("--out must be separate from the public video output directory")
    if (a.gif or a.no_render) and not a.encode:
        ap.error("--gif and --no-render require --encode")
    if a.count <= 0:
        ap.error("--count must be positive")
    if a.fps <= 0:
        ap.error("--fps must be positive")
    if a.encode and 90000 % a.fps:
        ap.error("--fps must divide the 90 kHz MP4 clock when encoding")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", a.product):
        ap.error("--product must be a prim name under /Render")
    if a.spp <= 0 or a.max_steps < 0:
        ap.error("--spp must be positive and --max-steps must be nonnegative")
    if a.gif and (a.gif_width <= 0 or a.gif_fps <= 0):
        ap.error("--gif-width and --gif-fps must be positive")
    try:
        a.frames = list(range(a.count)) if a.frames == "all" else [int(v) for v in a.frames.split(",")]
    except ValueError:
        ap.error("--frames must be 'all' or a comma list of integers")
    if not a.frames or len(set(a.frames)) != len(a.frames) or any(f < 0 or f >= a.count for f in a.frames):
        ap.error("--frames must contain distinct indices from 0 through --count minus one")
    if a.encode and a.frames != list(range(a.count)):
        ap.error("--encode requires the complete ordered sequence; omit --frames")
    try:
        a.res = tuple(int(v) for v in a.res.lower().split("x"))
    except ValueError:
        ap.error("--res must be WxH with positive integers")
    if len(a.res) != 2 or any(v <= 0 for v in a.res):
        ap.error("--res must be WxH with positive integers")
    if a.encode and not a.no_render and any(v % 2 for v in a.res):
        ap.error("--res dimensions must be even when encoding H.264")
    if not a.no_render and not a.scene.is_file():
        ap.error(f"scene does not exist: {a.scene}")
    return a


def main():
    a = parse_args()
    if not a.no_render:
        render(a.frames, a.res, a.spp, a.out.resolve(), a.max_steps or 4 * max(a.spp, 64) + 64,
               a.scene.resolve(), a.product, a.fps, a.count, a.supersample)
    if a.encode:
        encode(a.out.resolve(), a.gif_width, a.gif_fps, a.gif, a.fps, a.count, a.product)


if __name__ == "__main__":
    main()
