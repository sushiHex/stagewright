# stagewright

Parametric OpenUSD worlds, built from source. The repo will hold several procedural models; the first
(and so far only) one is described below. Its assets, scenes, documentation and public media live
under `models/wind_tunnel/`; shared helpers and command-line tools stay in `tools/`.

The first model is a presentation-quality open-jet automotive wind tunnel test section, authored in OpenUSD and rendered
headless with NVIDIA RTX (`ovrtx`). It is built to drop into the environment slot of NVIDIA's
real-time wind tunnel blueprint (`NVIDIA-Omniverse-blueprints/digital-twins-for-fluid-simulation`)
through one override layer. The plan and task list are in `docs/plan.md`. Read it before starting work.

## Narrative rule

The target (2026-10-26) is a 100% NVIDIA pipeline: OpenUSD Exchange SDK, ovrtx/ovstage, NVIDIA's USD
validator, the blueprint's own stage contract, Warp for computation, nvImageCodec for PNG/JPEG,
PyNvVideoCodec (NVENC) for MP4. The migration is task 10 in `docs/plan.md`. The only sanctioned
non-NVIDIA step is the optional GIF fallback (ffmpeg, behind a flag). Python, uv and numpy-as-container
stay; never claim "no numpy" or "100%" in the README, claim "every stage is NVIDIA".

## Hard rules

- **Never copy NVIDIA example scripts into this repo.** The ovrtx licence is an NVIDIA SLA
  (pre-release). Write our own calls against the documented API.
- **Never publish render times or any performance figure.** This covers the README, commits and
  captions (ovrtx LICENSE, benchmark clause).
- **Label it a conceptual presentation environment.** Only claim what was actually checked: that the
  layer composes, the transforms, the bounds, and a render from their camera. Never claim it runs
  inside the blueprint application.
- The repo name and commit messages never contain "nvidia". Commits stay neutral: no AI or process
  talk, and no Co-Authored-By or session trailers.
- Do not vendor the blueprint. Clone it to `external/` (gitignored) with `GIT_LFS_SKIP_SMUDGE=1`.
- The Ahmed body is a presentation prop. It lives in the presentation root, never inside the
  environment payload.
- Use CC0 assets only (Poly Haven). Record each asset and its licence in `models/wind_tunnel/docs/assets.md`.

## Stage contract (from the blueprint source, recorded 2026-10-26)

- Z-up, metersPerUnit 0.01 (centimetres), 60 timecodes per second.
- `/World/WindTunnel` payloads `layers/WindTunnel/windTunnelEnv.usd` with no prim target. The
  environment carries its own lights and ground, and the stage layers have none. A replacement must
  bring its own lights.
- The flow domain in world space is X -144..144, Y -650..430, Z -4..248 cm. Flow runs along world -Y,
  so the inlet is at Y +430 and the wake runs toward Y -650.
- CarHero: translate (0,250,0), rotateXYZ (90,0,0).
- CameraMAIN_00: translate (-776.9, 653.6, 411.0), rotateYXZ (70.68, 0, -125.66), focal 18.15,
  aperture 20.955 x 15.29.
- Override shape (an explicit list-op; never `prepend`, never clear-then-add):
  `over "World" { over "WindTunnel" ( payload = [@./models/wind_tunnel/assets/test_section.usda@</Environment>] ) {} }`
  in a root layer that sublayers their `Main.usda`.

## Environment

```
uv venv --python 3.13 .venv
uv pip install --python .venv/Scripts/python.exe "ovrtx==0.6.0.1791947691" "ovstage==0.3.0.1791986420" "usd-exchange==3.0.1" "usd-validation-nvidia==1.22.0" "numpy==2.5.4"
uv pip install --python .venv/Scripts/python.exe "pynvvideocodec==2.2.3" "nvidia-nvimgcodec-cu12[all]==0.9.0.20" "warp-lang==1.18.0"
.venv/Scripts/python.exe tools/smoke.py make
.venv/Scripts/python.exe tools/smoke.py render
```

PNG/JPEG writes use `tools/image_io.py` (nvImageCodec), including the smoke test and fixed
presentation outputs in `tools/build_media.py`. MP4 uses PyNvVideoCodec with NVENC and its
libav-based muxer; the ffmpeg executable is needed only for `tools/render_motion.py --encode --gif`.
Warp computes periodic spectral noise, material maps and the heavier mesh operations. numpy remains
for array exchange, USD packing and diagnostic checks. Run `tools/check_compute.py` for numerical
and codec regressions. `tools/check_presentation.py` checks authored motion and framing. Motion uses
Warp filtered downsampling with `--supersample 2`; `--res` remains the output size. Optional task
10e is deferred pending dataset acceptance and download approval.

- **Run throwaway probe scripts with `python -I`.** A stray `warp.py` sitting next to a probe script
  shadowed the real `warp` package on 2026-10-26. Never name a file in `tools/` after a package.

- **Do not install `usd-core`.** `usd-exchange` (NVIDIA's OpenUSD Exchange SDK) bundles its own
  OpenUSD 26.8 `pxr` and warns that usd-core conflicts with it. Author through `usdex.core` helpers
  where they exist, and fall back to plain `pxr` otherwise.
- Validate every asset with `.venv/Scripts/nvidia_usd_validate.exe <file>` before handing it on.
- Author with `pxr` and render with ovrtx in **separate processes**, since ovrtx bundles its own USD
  runtime.
- Always set `omni:rtx:rendermode = "PathTracing"` on the RenderProduct (ovrtx issue #5: black frames
  on Ampere).
- The first run compiles shaders and is slow. Later runs use the cache.
- **Camera motion:** author the camera as time samples, then per frame call
  `population.update_from_usd_time(stage, ordinal=n, time=frame / tcps)` (time is in SECONDS),
  `advance_write_floor(n)`, then `step(ordinal=n)`. No `compute_hierarchy` is needed under the RENDERING
  domain. Writing `omni:xform` with `Stage.write_attribute` per ordinal also works. The old "same pose"
  smoke frames were a symmetric scene (a 90-degree orbit of a centred cube looks identical), not a
  renderer bug: keep a motion test asymmetric, and check that the image changes, not just the numbers.
- **ovrtx rendering facts (tested 2026-10-26):**
  - Exposure: use the camera's `exposure:fStop`, `exposure:time` and `exposure:iso`. A plain
    `exposure` does nothing. The default is f/5, 1/50 s, ISO 100.
  - RectLights are invisible to the camera, so pair each one with an emissive mesh. Emissive 1.0 lights
    the floor about as much as RectLight intensity 170, so use `emissive = intensity / 170`.
  - Relative texture paths resolve through both a reference and a payload.
  - PointInstancer renders, but prototypes at the origin sit inside the flow domain. Merge meshes or
    park prototypes outside it.
- **A default `Gf.Rotation()` has an undefined axis** in the bundled pxr. Combined with a scale, it
  intermittently writes a NaN matrix. Always pass an explicit identity rotation. The build scripts
  refuse to save a file that contains NaN.
- `usdex` authors arcs as `prepend references` / `prepend payload`. That is fine in our own roots, but
  the blueprint override must use the explicit `payload = [...]` list-op.
- **Validator:** the rule that wants USDA arrays over 64 elements stored as binary cannot pass while
  the assets stay USDA text. It is accepted. Every other rule must be clean.
- Windows, Python 3.13 (`python`, not `python3`). Use forward slashes in paths.
