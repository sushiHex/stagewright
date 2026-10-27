# Render an animated camera frame by frame with ovrtx (headless RTX path tracing).
#   python tools/render_motion.py --frames 0,107,215 --spp 16 --out build/frames/dolly_test
#   python tools/render_motion.py --res 1280x720 --spp 64
#   python tools/render_motion.py --product Orbit360 --encode
#   python tools/render_motion.py --encode          render and encode build/frames/dolly to MP4
#
# Runs in its own process (never imports pxr). Per CLAUDE.md "Camera motion": for each frame the
# sampled properties advance to time frame / fps SECONDS on a new ordinal, the write floor is
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
from project_paths import ROOT, SCENES, MOTION_SETTINGS  # noqa: E402

SCENE = SCENES / "present.usda"
FRAMES = ROOT / "build" / "frames" / "dolly"
OUT = ROOT / "build" / "out"
PRODUCT = "Dolly"
FPS = MOTION_SETTINGS[PRODUCT]["fps"]
COUNT = MOTION_SETTINGS[PRODUCT]["frames"]
WARMUP_PASSES = 2


def frame_directory(product):
    return ROOT / "build" / "frames" / product.lower()


def motion_timing(product, fps, count):
    settings = MOTION_SETTINGS.get(product, MOTION_SETTINGS[PRODUCT])
    return settings["fps"] if fps is None else fps, settings["frames"] if count is None else count


def loop_enabled(product, loop):
    settings = MOTION_SETTINGS.get(product)
    if settings is not None:
        if loop and not settings["loop"]:
            raise ValueError(f"{product} is not authored as a loop")
        return settings["loop"]
    return bool(loop)


def canonical_sequence(scene, product, fps, count, loop):
    settings = MOTION_SETTINGS.get(product)
    return (scene.resolve() == SCENE.resolve() and settings is not None
            and fps == settings["fps"] and count == settings["frames"] and loop == settings["loop"])


def check_frame_directory(scene, product, fps, count, loop, directory):
    protected = {frame_directory(name).resolve() for name in MOTION_SETTINGS}
    if directory.resolve() in protected:
        own_directory = frame_directory(product).resolve()
        if directory.resolve() != own_directory or not canonical_sequence(scene, product, fps, count, loop):
            raise ValueError("Custom scenes and alternate settings require --out outside the built-in frame directories")


def warmup_frames(start, count, loop):
    if loop:
        # Load the full orbit's visible content, then approach the start in playback order.
        quarters = list(dict.fromkeys((start + part * count // 4) % count for part in range(4)))
        tail = [(start - step) % count for step in (3, 2, 1)]
        return quarters + tail * WARMUP_PASSES
    warm = []
    for k in (3, 2, 1):
        if start + k < count:
            warm.append(start + k)
        elif start - k >= 0:
            warm.append(start - k)
    return warm * WARMUP_PASSES


def render(frames, res, spp, out_dir, max_steps, scene=SCENE, product=PRODUCT,
           fps=None, count=None, supersample=2, loop=None, cpu_readback=False,
           sample_batch=stills.DEFAULT_SAMPLE_BATCH):
    frames = list(frames)
    fps, count = motion_timing(product, fps, count)
    loop = loop_enabled(product, loop)
    check_frame_directory(scene, product, fps, count, loop, out_dir)
    import numpy as np
    from image_io import ImageCodec
    from image_compute import RGBDownsampler

    import rtx as rt

    out_dir.mkdir(parents=True, exist_ok=True)
    render_res = tuple(size * supersample for size in res)
    layer = stills.write_override(scene, [product], render_res, spp, ghost=False, qc=False,
                                  sample_batch=sample_batch)
    product = f"/Render/{product}"
    # Warm-up poses are discarded. Loop guards repeat the first two poses after one full
    # cycle for a photometric seam check, and are deliberately outside the numeric sequence.
    warm = warmup_frames(frames[0], count, loop)
    schedule = [(f, None) for f in warm] + [(f, f"{f:04d}.png") for f in frames]
    if loop and frames == list(range(count)):
        schedule += [(f, f"_loop_{f:04d}.png") for f in range(min(2, count))]
    downsampler = RGBDownsampler(supersample) if supersample > 1 else None
    read_pixels = None if downsampler is None else (downsampler.capture_cpu if cpu_readback else downsampler.capture)
    with rt.open_renderer() as rtx, rt.loaded_scene(rtx, "motion", layer) as loaded, ImageCodec() as codec:
        # Ordinal 1 is the initial load; each scheduled pose gets the next ordinal.
        for ordinal, (f, filename) in enumerate(schedule, start=2):
            rt.seek(loaded, ordinal, f / fps)
            images, status = rt.converge(rtx, [product], ordinal, delta_time=1 / fps, max_steps=max_steps,
                                        capture=filename is not None, read_pixels=read_pixels)
            if product not in images:
                raise RuntimeError(f"frame {f}: no image captured (last status {status.get(product)})")
            if filename is None:
                continue
            px = images[product]
            progression, converged = status[product]
            rgb = px[..., :3].astype(np.float32)
            codec.write_rgb(out_dir / filename, px)
            label = "loop guard" if filename.startswith("_loop_") else "frame"
            print(f"{label} {f:4d} ordinal {ordinal:4d} progression={progression} converged={converged} "
                  f"mean={rgb.mean():.1f}", flush=True)


def encode(frames_dir, gif_width, gif_fps, make_gif=False, fps=None, count=None,
           product=PRODUCT, scene=SCENE, loop=None):
    fps, count = motion_timing(product, fps, count)
    loop = loop_enabled(product, loop)
    settings = MOTION_SETTINGS.get(product)
    if scene.resolve() == SCENE.resolve() and settings is not None and settings["loop"] and (fps != settings["fps"] or count != settings["frames"]):
        raise ValueError(f"{product} encoding requires its authored fps and complete frame count")
    frames_dir = frames_dir.resolve()
    check_frame_directory(scene, product, fps, count, loop, frames_dir)
    canonical = (frames_dir == frame_directory(product).resolve()
                 and canonical_sequence(scene, product, fps, count, loop))
    # Only each complete default presentation sequence may replace its public media source.
    # Preview and custom-scene videos stay with their explicitly selected frame directory.
    video_dir = OUT if canonical else frames_dir
    mp4, gif = video_dir / f"{product.lower()}.mp4", video_dir / f"{product.lower()}.gif"
    public_videos = {(OUT / f"{name.lower()}.mp4").resolve() for name in MOTION_SETTINGS}
    if not canonical and mp4.resolve() in public_videos:
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
    ap.add_argument("--fps", type=int, help="sample and playback frame rate (authored product default)")
    ap.add_argument("--count", type=int, help="number of frames in the complete sequence (authored product default)")
    ap.add_argument("--loop", action="store_true", default=None,
                    help="periodic generic sequence; Orbit360 enables this automatically")
    ap.add_argument("--frames", default="all", help="'all' or a comma list of frame numbers")
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--spp", type=int, default=64)
    ap.add_argument("--supersample", type=int, choices=(1, 2), default=2,
                    help="render scale before Warp filtered downsampling; --res is the output size")
    ap.add_argument("--sample-batch", type=int, default=stills.DEFAULT_SAMPLE_BATCH,
                    help="sample batch limit; uses a divisor of --spp; 1 retains the reference launch schedule")
    ap.add_argument("--cpu-readback", action="store_true",
                    help="compatibility/reference path: filter after CPU readback")
    ap.add_argument("--out", type=Path,
                    help="frame directory; custom/preview videos are written here too")
    ap.add_argument("--max-steps", type=int, default=0, help="step cap per frame; default 4 x spp + 64")
    ap.add_argument("--encode", action="store_true", help="encode the complete frame sequence in --out to MP4")
    ap.add_argument("--no-render", action="store_true", help="with --encode, skip rendering")
    ap.add_argument("--gif", action="store_true", help="also encode a GIF with ffmpeg (requires --encode)")
    ap.add_argument("--gif-width", type=int, default=640)
    ap.add_argument("--gif-fps", type=int, default=12)
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", a.product):
        ap.error("--product must be a prim name under /Render")
    a.fps, a.count = motion_timing(a.product, a.fps, a.count)
    a.out = frame_directory(a.product) if a.out is None else a.out
    try:
        a.loop = loop_enabled(a.product, a.loop)
        check_frame_directory(a.scene, a.product, a.fps, a.count, a.loop, a.out)
    except ValueError as error:
        ap.error(str(error))
    public_videos = {(OUT / f"{name.lower()}.mp4").resolve() for name in MOTION_SETTINGS}
    if (a.out / f"{a.product.lower()}.mp4").resolve() in public_videos:
        ap.error("--out must be separate from the public video output directory")
    authored = MOTION_SETTINGS.get(a.product)
    if a.encode and a.scene.resolve() == SCENE.resolve() and authored is not None and authored["loop"]:
        if a.fps != authored["fps"] or a.count != authored["frames"]:
            ap.error(f"{a.product} encoding requires its authored fps and complete frame count")
    if (a.gif or a.no_render) and not a.encode:
        ap.error("--gif and --no-render require --encode")
    if a.count <= 0:
        ap.error("--count must be positive")
    if a.fps <= 0:
        ap.error("--fps must be positive")
    if a.encode and 90000 % a.fps:
        ap.error("--fps must divide the 90 kHz MP4 clock when encoding")
    if a.loop and a.count < 2:
        ap.error("--loop requires at least two frames")
    if a.sample_batch < 1:
        ap.error("--sample-batch must be positive")
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
               a.scene.resolve(), a.product, a.fps, a.count, a.supersample, a.loop, a.cpu_readback, a.sample_batch)
    if a.encode:
        encode(a.out.resolve(), a.gif_width, a.gif_fps, a.gif, a.fps, a.count, a.product, a.scene.resolve(), a.loop)


if __name__ == "__main__":
    main()
