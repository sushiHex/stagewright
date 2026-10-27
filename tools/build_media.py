"""Refresh public media from the presentation scene's fixed output paths."""
from pathlib import Path
import shutil

from image_io import read_rgb, write_rgb

from project_paths import ROOT, MODEL


def main():
    # A fixed allowlist keeps blueprint-car renders in build/private out of media.
    for name in ("hero", "detail", "main", "wake", "qc_main"):
        write_rgb(MODEL / "media" / f"{name}.jpg",
                  read_rgb(ROOT / "build" / "stills" / f"final_{name}.png"))
    shutil.copyfile(ROOT / "build" / "out" / "dolly.mp4", MODEL / "media" / "dolly.mp4")


if __name__ == "__main__":
    main()
