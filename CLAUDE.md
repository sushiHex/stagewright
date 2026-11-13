# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# stagewright

Parametric OpenUSD worlds, built from source. A prompt shapes editable Python generators; NVIDIA
libraries build the scene, simulate its mechanisms and render the result. Models live under
`models/<name>/`: `wind_tunnel` (assets, scenes, docs, public media), `courtyard` (the accepted
COURTYARD generator and build guide) and `inspection_hall` (built on the COURTYARD helpers). Shared
helpers and command-line tools stay in `tools/`. The mecha-factory study (Issue #51) is private work
under ignored `build/`; it is not a packaged model.

## Start here

- Read `docs/plan.md` (active experiment first), then the top of `docs/handoff.md`. The handoff is a
  long reverse-chronological log; read only "Where things stand" unless a task needs older history.
  GitHub Issues and Milestones hold the live status.
- **Check the checkout before trusting local files.** Run `git fetch` and
  `git rev-list --left-right --count HEAD...origin/main`. The owner's primary checkout can sit on an
  old branch, behind `main`, with preserved uncommitted edits and untracked copies of files that
  have since merged. Compare with `git show origin/main:<path>` when a file looks stale or missing.
  Never reset, stash, clean or commit that whole tree. Start each change in a new worktree and
  branch from `origin/main`, and carry over only the files the change needs.
- Everything under `build/` is ignored and private: `build/experiments/` (frozen trial inputs and
  records), `build/candidates/` (review pages and media), `build/checks/` (evidence and probes),
  `build/private/` (renders showing the blueprint's own car), `build/envs/` (optional environments).
  Do not publish, commit or quote measurements from it.

## Architecture

The harness is a chain of small CLIs that exchange files. No process hosts two runtimes.

| Process | Python | May import | Tools |
|---|---|---|---|
| Author, pack, measure | `.venv` | `pxr` / `usdex` (from `usd-exchange`), Warp, numpy | `build_env.py`, `build_present.py`, `models/*/build.py`, `physics_usd.py`, `publish.py`, `sample_transforms.py`, `viewer_scene.py`, `fit_check.py` |
| Render, encode | `.venv` | `ovrtx` / `ovstage`, codecs; never `pxr` | `rtx.py`, `render.py`, `render_motion.py`, `smoke.py render`, `observe.py` |
| Physics | `build/envs/physics` | `ovphysx`, `ovstage`; no `pxr` | `simulate.py` |

A render tool that needs authoring runs it in a child process (`render_motion.py --snapshot-poses`
calls `sample_transforms.py`; `observe.py` calls `viewer_scene.py`). `engine.py` runs in the author
process and starts the physics worker with the Python given by `--physics-python`.

The recorded-motion flow, used by every mechanism study:

1. A generator writes a static scene plus `candidates/<name>.usda` and a matched motor-disabled
   control. The control changes only drive stiffness, damping and maximum force.
2. `tools/engine.py <candidate> <new-dir> --physics-python ...` packs an immutable `input.usdz`,
   runs `simulate.py`, and writes `recording/poses.npz`, `recording/replay.usdc`, `worker.log` and
   `feedback.json` (per-body travel and rotation only, not a verdict). It refuses an existing
   destination.
3. The model's own measure script (`models/courtyard/source/measure.py`,
   `models/inspection_hall/source/measure.py`) tests the declared operating condition on the CPU
   from the frozen USD and recorded poses. Both use conservative projected bounds: a pass
   establishes the condition, a fail means only that the measure did not establish it.
4. A view root sublayers the replay above the display scene and copies the replay's stage metadata.
   `render_motion.py --snapshot-poses` renders each recorded pose through a fresh stage;
   a second `--no-render --encode` call builds the MP4. See `docs/recorded-pose-capture.md`.

`tools/rtx.py` is the only layer over ovrtx/ovstage: `converge()` steps a product until the frame
reports converged and raises if a capture does not. Every GPU entry point constructs
`gpu_work.GpuPacer` (stop file, priority, affinity, pacing between completed native calls).
`tools/project_paths.py` holds the default model and the per-product motion cadence; there is no
model registry. `publish.py` and `observe.py` form the optional live observer (`docs/live-viewer.md`).

The wind-tunnel model is a presentation-quality open-jet automotive wind tunnel test section, authored in OpenUSD and rendered
headless with NVIDIA RTX (`ovrtx`). It is built to drop into the environment slot of NVIDIA's
real-time wind tunnel blueprint (`NVIDIA-Omniverse-blueprints/digital-twins-for-fluid-simulation`)
through one override layer. The plan and task list are in `docs/plan.md`. Read it before starting work.

## Design principle

**SIMPLIFICATION IS PROGRESS.**

Keep Stagewright a light, direct harness for a 100% NVIDIA core scene pipeline. Reusing NVIDIA
open-source technology and the wider OpenUSD ecosystem, especially NVIDIA-origin components,
is part of the mission. Prefer those components over bespoke equivalents when they serve the
scene, simulation or live experience. Follow applicable NVIDIA USD and library guidance with
only the structure the current use needs. Keep the application glue small. Enforce YAGNI
over TDD: implement the current need with the smallest clear change, then prove the behavior that
matters. Tests serve the implementation; they do not drive speculative architecture.

- Prefer direct SDK calls, simple functions and the existing CLI tools.
- Add an abstraction, dependency or option only when a concrete use requires it.
- Fix observed failures at their source. Prefer a local guard over a new validation system.
- Verify changed behavior with a focused probe, smoke run or visual inspection. Add a regression
  check only when it protects a consequential failure that is likely to recur.
- Do not add manifests, compliance layers, workflow engines, broad test suites, automatic CPU
  fallbacks or release infrastructure without a demonstrated need.
- Existing checks are tools to use when relevant, not a checklist to expand or rerun for every edit.
- Prefer video when showing results with motion, and looping playback for mini demos. Present local
  files with their full absolute paths. Use full absolute paths as link labels when possible.
- For comparisons, use one aligned fixed view and step through the saved passes. Keep the
  lossless source images and avoid camera moves. Prefer image quality over small media files.
  Use a flipbook cadence, selectable pass buttons and a clear active state. Retain meaningful
  intermediate complete saves during future construction; do not invent construction history.
  Every comparison step must show a visible change. Omit saves that repeat the same visible state.
- Physics demonstrations must tell the story established by the environment. Give each mechanism
  a clear role in the scene's assembly, service, operation or testing.

Preserve the hard rules below and the separation of authoring and rendering processes.

## Construction experiments

Keep planning and peer review separate from construction trials. Each trial starts in a fresh
session with the exact brief and a frozen, declared set of starting files and reference material.
Use Hardline Codex default mode with `context="clean"`, `write=True` and that frozen copy as
`workdir`. The copy needs its own real `.git` directory; a linked Git worktree is not supported.
Pin the full model ID and effort on every call. Advisory mode cannot provide construction
write access. Claude clean writes remain unsupported.

Keep one small record containing:

- The exact prompt, starting revision, pre-run workdir content hash and declared references.
- Returned `requested_model`, `requested_effort`, `actual_model`, `effective_effort`,
  `model_resolution` and execution mode exactly as supplied; preserve null as unknown.
- `instructions_note`, requested/selected provider, quota redirection and fallback metadata.
- The returned `context` report, including configured/discovered/observed evidence and limits.
- The first result, transcript and resulting artifacts, before human or peer feedback.

Codex clean runs are ephemeral, have no MCP servers or connectors, and exclude the user's
Codex home/configuration. Freeze workspace instructions with the inputs. Retain `context.not_removed`:
system/managed configuration, environment, external skills, web search and other documented
sources remain possible. Clean context is not filesystem confinement. The context report's
observed field currently establishes thread startup, not instruction ingestion. Preserve any
`instructions_note` about the Windows AGENTS-loading retry. Claude global instructions and
auto-memory loading remain unverified. Keep private external context out of the repository.

Codex `actual_model` and `effective_effort` are unknown; model resolution identifies only the
configured model. Claude reports the served model, but effective effort is unknown for both.
Retain routing evidence even when pinned. Record execution feedback explicitly; coached
revisions and model changes are separate iterations. These controls belong to the experiment
runner, leaving the construction agent free to solve the brief.

A trial may explicitly allow the constructor to invoke a frozen engine tool and read its own
execution feedback. Preserve the initial authored candidate before physical evaluation, each
evaluated revision and the actual feedback consumed. This measures construction with execution
feedback; later human or peer coaching remains a separately labelled iteration. The viewer stays
an observer. Keep this permission and the tool contract in the declared inputs.

## Work planning

When proposing a work scope or PM next steps, aim for at least four concrete tasks.
Keep each task tied to a useful outcome; avoid padding the scope or adding speculative work.

Spend the session model on planning, briefs, independent assessment of results and review.
Construction runs as a separate clean trial (above). Before committing to a design or a causal
diagnosis, have a second model attack it and record where the two disagree. A plan names the one
measured bottleneck or owner request it serves, the single change to try, the check that would
reject it and the evidence to keep.

## GitHub workflow

- Track concrete work in Issues and group related deliverables in Milestones.
- Use a branch and focused PR for each change, linking its Issue with `Closes #...`.
- Keep PR descriptions brief: the problem, the change and the checks actually run.
- GitHub holds active work status; planning docs hold design context and handoff notes.
- Commit only when requested. Push and merge only within the owner's authorization; review the
  final PR diff before merging. Keep the existing neutral commit-message rules.

## Narrative rule

The target (2026-10-26) is a 100% NVIDIA pipeline: OpenUSD Exchange SDK, ovrtx/ovstage, NVIDIA's USD
validator, the blueprint's own stage contract, Warp for computation, nvImageCodec for PNG/JPEG,
PyNvVideoCodec (NVENC) for MP4. The migration is task 10 in `docs/plan.md`. The only sanctioned
non-NVIDIA step is the optional GIF fallback (ffmpeg, behind a flag). Python, uv and numpy-as-container
stay. The README may emphasize a "100% NVIDIA core scene pipeline" when its scope is explicit:
authoring APIs, computation, validation, RTX rendering and PNG/JPEG/MP4 output. Keep Python, uv,
NumPy, the prompt-to-code agent and optional FFmpeg GIF outside that claim. Never imply that
all software dependencies or the coding agent are NVIDIA products, or claim "no numpy".

## Hard rules

- **Never copy NVIDIA example scripts into this repo.** The ovrtx licence is an NVIDIA SLA
  (pre-release). Write our own calls against the documented API.
- **Never publish render times or any performance figure.** This covers the README, commits and
  captions (ovrtx LICENSE, benchmark clause).
- **Use vram-mcp before touching the GPU**, including physics initialization, rendering and encoding.
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

`requirements.txt` is the pinned dependency list. Keep its versions aligned with the technical guide.

```
uv venv --python 3.13 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe tools/smoke.py make
.venv/Scripts/python.exe tools/smoke.py render
```

Build a model and run one check at a time; none of these is a suite to run after every edit.

```
.venv/Scripts/python.exe tools/build_env.py                      # wind tunnel asset; textures use the GPU
.venv/Scripts/python.exe tools/build_present.py                  # its presentation roots
.venv/Scripts/python.exe models/courtyard/build.py --out build/courtyard
.venv/Scripts/python.exe -I -B models/inspection_hall/build.py --out build/inspection-hall
.venv/Scripts/nvidia_usd_validate.exe models/wind_tunnel/assets/test_section.usda
.venv/Scripts/python.exe tools/fit_check.py --strict             # needs external/blueprint
.venv/Scripts/python.exe tools/check_presentation.py             # authored motion and framing, CPU
.venv/Scripts/python.exe tools/check_gpu_work.py                 # pacing, stop file, affinity; CPU only
.venv/Scripts/python.exe tools/check_compute.py                  # Warp numerics and codecs, GPU
.venv/Scripts/python.exe tools/check_loop.py                     # Orbit360 seam, after a full render
.venv/Scripts/python.exe tools/render.py --products Hero --res 960x540 --spp 64
.venv/Scripts/python.exe tools/render_motion.py --frames 0,60,120 --out build/<new-dir>
```

Preview a bounded `--frames` selection before any full sequence. Only the complete canonical
Dolly and Orbit360 sequences write `build/out/*.mp4`, which `build_media.py` copies to public media;
custom scenes need their own `--out`. The full wind-tunnel rebuild order is in `docs/handoff.md`
("Rebuild from scratch"). Model guides hold each model's physics and capture commands.

PNG/JPEG writes use `tools/image_io.py` (nvImageCodec), including the smoke test and fixed
presentation outputs in `tools/build_media.py`. MP4 uses PyNvVideoCodec with NVENC and its
libav-based muxer; the ffmpeg executable is needed only for `tools/render_motion.py --encode --gif`.
Warp computes periodic spectral noise, material maps and the heavier mesh operations. numpy remains
for array exchange, USD packing and diagnostic checks. Run `tools/check_compute.py` for numerical
and codec regressions. `tools/check_presentation.py` checks authored motion and framing. Motion uses
Warp filtered downsampling with `--supersample 2`; `--res` remains the output size. Optional task
10e is deferred pending dataset acceptance and download approval.

### Desktop GPU work

Shared GPU workers use `tools/gpu_work.py`: Windows below-normal CPU priority, GPU
idle scheduling priority and idle time between completed calls. `STAGEWRIGHT_GPU_DUTY` sets
that wall-time budget (default `0.25`). It is not a hardware utilization ceiling.
Windows workers use at most four allowed logical CPUs, or half the system CPUs on smaller
systems. The affinity limit applies before native initialization and is inherited by children.
Keep the desktop default on this machine; coordinate any dedicated full-load run.
PathTracing can complete a whole image inside one native call. Its existing sample
settings and renderer clock remain unchanged; pacing applies after completed calls.
Use the same pacing in private capture loops. VRAM checks and reservations still apply.

Create `build/STOP_GPU` to stop these workers at the next checkpoint. The stop file
also interrupts idle waits and blocks new workers. Remove it deliberately to allow
work again. A native batch already running must finish or its process must be stopped.
Do not change global GPU clocks, power limits or desktop settings for a job.

### Optional physics worker

The owner approved NVIDIA tools for this project. `requirements-physics.txt` pins the optional
worker separately; keep the production author/renderer environment unchanged. The physics environment
uses ovstage population without pxr. Use vram-mcp and reserve capacity before GPU work.

```
uv venv --python .venv/Scripts/python.exe --no-python-downloads build/envs/physics
uv pip install --python build/envs/physics/Scripts/python.exe -r requirements-physics.txt
.venv/Scripts/python.exe tools/probe_mechanism.py build/probes/physics/input.usda
.venv/Scripts/python.exe tools/physics_usd.py pack build/probes/physics/input.usda build/probes/physics/input.usdz
build/envs/physics/Scripts/python.exe tools/simulate.py build/probes/physics/input.usdz --out build/probes/physics/result
.venv/Scripts/python.exe tools/physics_usd.py replay build/probes/physics/result
```

Use new output paths. Native USDZ packaging freezes composed layers and asset dependencies, allowing
one input checksum to identify the simulated content. The pose-only worker uses DirectGPU and records
actual pose-array devices, fixed-step samples and package versions. Replay supports static, unit-scale
body frames; it resets transform inheritance for recorded world poses. Authored body-frame animation,
scale/shear, contacts and runtime controls beyond authored constant drives are not established by this
readiness probe. The zero-gravity four-bar and no-drive control prove a constrained mechanical
dependency, not a completed hall, loaded mechanism, structure or model-construction trial.

- **Run throwaway probe scripts with `python -I`.** A stray `warp.py` sitting next to a probe script
  shadowed the real `warp` package on 2026-10-26. Never name a file in `tools/` after a package.

- **Do not install `usd-core`.** `usd-exchange` (NVIDIA's OpenUSD Exchange SDK) bundles its own
  OpenUSD 26.8 `pxr` and warns that usd-core conflicts with it. Author through `usdex.core` helpers
  where they exist, and fall back to plain `pxr` otherwise.
- Use `.venv/Scripts/nvidia_usd_validate.exe <file>` for changed USD assets when checking authoring
  correctness or integration. Documentation-only changes do not require asset validation.
- Author with `pxr` and render with ovrtx in **separate processes**, since ovrtx bundles its own USD
  runtime.
- Final captures use `omni:rtx:rendermode = "PathTracing"` on the RenderProduct. The upstream ovrtx
  issue #5 reports black RT2 output on Linux/Ampere. Local Windows/Ampere RT2 smoke and hall-still
  probes produce lit output, but final-image parity and motion quality remain unproved. See Issue #8.
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
- **Wind-tunnel validator:** the rule that wants USDA arrays over 64 elements stored as binary cannot
  pass while those assets stay USDA text. It is accepted. Every other wind-tunnel rule must be clean.
  COURTYARD and the inspection hall preserve accepted source with validation findings listed in
  their model guides. Do not claim that either passes the default validator preset.
- **Never open a second USD source on a populated ovstage Stage.** `open_usd` keeps prior prims and
  attributes. Use a fresh Stage per source, as the shared loaders do.
- **Write generated layer paths anchored**, as `./x` or `../x`. A bare `x` or `dir/x` is a search
  path, and a strict bundle walk refuses it.
- Run `fit_check.py` only where `external/blueprint` is a real directory under the checkout. Through
  a junction or symlink its path filter misfires and reports a false failure.
- Retained-stage time updates were unreliable for recorded rigid-body replays. Use
  `--snapshot-poses` for them; the default time-update path remains for authored camera motion.
- Windows, Python 3.13 (`python`, not `python3`). Use forward slashes in paths.
