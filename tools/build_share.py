"""Prepare local review/source archives from explicit first-party paths only."""
import hashlib
import json
from pathlib import Path
import zipfile

from project_paths import ROOT, MODEL, MOTION_SETTINGS

OUT = ROOT / "build" / "share"
MEDIA = [MODEL / "media" / f"{name}.jpg" for name in ("hero", "detail", "main", "wake", "qc_main")]
MEDIA += [MODEL / "media" / f"{name.lower()}.mp4" for name in MOTION_SETTINGS]
MODEL_DOCS = [MODEL / "docs" / name for name in ("assets.md", "fit-check.md", "guide.md")]
OVERRIDE = MODEL / "scenes" / "blueprint_override.usda"
README_VISUAL = ROOT / "docs" / "assets" / "nvidia-pipeline.svg"

INDEX = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>stagewright review</title>
<style>
body{font:16px/1.55 system-ui,sans-serif;background:#17191c;color:#eceef1;margin:0}
main{max-width:1100px;margin:auto;padding:32px 20px}h1{font-size:32px;line-height:1.2}
a{color:#f4b27a}img,video{width:100%;height:auto;display:block;border-radius:6px}
section{margin:32px 0}.note{color:#b9bec6;max-width:78ch}nav a{margin-right:20px}
</style><main>
<h1>stagewright</h1>
<p>Parametric OpenUSD worlds, built from source.</p>
<p class="note">A conceptual open-jet wind-tunnel presentation environment with a procedural
Ahmed-style reference body. Composition, transforms, bounds, camera framing and renders were checked.
It has not been run inside the blueprint application.</p>
<img src="models/wind_tunnel/media/hero.jpg" alt="Reference body, nozzle and honeycomb in the open-jet test section">
<section><h2>Accepted dolly</h2>
<video controls playsinline preload="metadata" src="models/wind_tunnel/media/dolly.mp4"></video>
<p class="note">The accepted pass from behind the body to beyond its nose.</p></section>
<section><h2>360 degree loop</h2>
<video controls loop muted playsinline preload="metadata" src="models/wind_tunnel/media/orbit360.mp4"></video>
<p class="note">A wide dolly/crane tour reveals the nozzle, turntable, collector and hall. Repeat is enabled in this player. The encoded sequence
contains unique views, with no duplicate endpoint or endpoint pause.</p></section>
<nav><a href="README.md">Project README</a>
<a href="models/wind_tunnel/docs/fit-check.md">Fit report</a>
<a href="models/wind_tunnel/docs/assets.md">Assets and references</a>
<a href="LICENSE">MIT licence</a></nav>
<section class="note">Original code and generated content are MIT licensed. Dependencies retain
their own terms and are not bundled. Fine-pattern shimmer can remain at some viewing sizes.
The review archive contains media and verification notes; rebuilding requires the source archive
and the dependencies described in the README.</section>
</main></html>
"""

NOTE = """stagewright: conceptual OpenUSD open-jet presentation environment

Open index.html to view the hero image, accepted dolly and loopable 360 shot.
README.md explains the project and build. The model docs contain fit checks and asset references.
Original code and generated content are MIT licensed; dependencies keep their own terms.

Verified: stage composition, transforms, bounds, camera paths/framing and headless renders.
Not verified: running inside the blueprint application or aerodynamic behavior.
Fine-pattern shimmer remains a visual limitation at some playback sizes.
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_bytes(path):
    path = Path(path)
    relative = path.relative_to(ROOT)
    resolved = path.resolve()
    if (not resolved.is_relative_to(ROOT) or relative.parts[0] in ("build", "external", ".venv", ".git")
            or resolved.relative_to(ROOT).parts[0] in ("build", "external", ".venv", ".git")
            or path.is_symlink()):
        raise ValueError(f"Not a public first-party source path: {relative}")
    return relative.as_posix(), path.read_bytes()


def archive(name, paths):
    entries = dict(source_bytes(path) for path in paths)
    entries.update({"index.html": INDEX.encode(), "share_note.txt": NOTE.encode()})
    entries["SHA256SUMS.txt"] = ("".join(f"{digest(data)}  {path}\n" for path, data in sorted(entries.items()))).encode()
    temporary = OUT / f"{name}.partial.zip"
    result = OUT / f"{name}.zip"
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for path, data in sorted(entries.items()):
                info = zipfile.ZipInfo(path)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, data)
        with zipfile.ZipFile(temporary) as zipped:
            if zipped.testzip() is not None or set(zipped.namelist()) != set(entries):
                raise RuntimeError("Archive integrity or entry list differs")
            for path, data in entries.items():
                if digest(zipped.read(path)) != digest(data):
                    raise RuntimeError(f"Archive content differs: {path}")
        temporary.replace(result)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return result


def main():
    # A verification record is generated only after the full canonical loop, guard
    # images and decoded video have passed tools/check_loop.py.
    record = json.loads((ROOT / "build" / "checks" / "orbit360_verified.json").read_text())
    if record["video_sha256"] != digest((MODEL / "media" / "orbit360.mp4").read_bytes()):
        raise RuntimeError("Public loop differs from the verified video; refresh media first")
    if record["scene_sha256"] != digest((MODEL / "scenes" / "present.usda").read_bytes()):
        raise RuntimeError("Loop verification is stale for the current scene")
    if not (ROOT / "LICENSE").read_text().startswith("MIT License\n"):
        raise RuntimeError("Expected the selected MIT licence")
    OUT.mkdir(parents=True, exist_ok=True)
    review = [ROOT / "LICENSE", ROOT / "README.md", README_VISUAL, *MEDIA, *MODEL_DOCS, OVERRIDE]
    texture_names = ("belt", "concrete", "epoxy", "honeycomb", "perf", "turntable")
    textures = [MODEL / "assets" / "textures" / f"{name}_{kind}.png"
                for name in texture_names for kind in ("color", "normal", "orm")]
    sources = [*review, ROOT / "CLAUDE.md", ROOT / "requirements.txt", ROOT / ".gitignore", ROOT / ".gitattributes",
               *(ROOT / "docs").glob("*.md"), *(ROOT / "tools").glob("*.py"),
               MODEL / "assets" / "test_section.usda", *textures,
               MODEL / "scenes" / "present.usda", MODEL / "scenes" / "present_payload.usda"]
    for result in (archive("stagewright-review", review), archive("stagewright-source", sources)):
        print(result)


if __name__ == "__main__":
    main()
