"""Refresh public media from the presentation scene's fixed output paths."""
from pathlib import Path
import shutil

from gpu_work import GpuPacer

from project_paths import ROOT, MODEL, PUBLIC_STILLS, MOTION_SETTINGS


def main():
    gpu = GpuPacer()
    from image_io import read_rgb, write_rgb

    # A fixed allowlist keeps blueprint-car renders in build/private out of media.
    for name in PUBLIC_STILLS:
        with gpu.batch():
            write_rgb(MODEL / "media" / f"{name}.jpg",
                      read_rgb(ROOT / "build" / "stills" / f"final_{name}.png"))
    for product in MOTION_SETTINGS:
        name = product.lower() + ".mp4"
        shutil.copyfile(ROOT / "build" / "out" / name, MODEL / "media" / name)


if __name__ == "__main__":
    main()
