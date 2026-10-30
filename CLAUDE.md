# stagewright

Parametric OpenUSD worlds, built from source. The repo will hold several procedural models; the first
(and so far only) one is described below. Its assets, scenes, documentation and public media live
under `models/wind_tunnel/`; shared helpers and command-line tools stay in `tools/`.

The first model is a presentation-quality open-jet automotive wind tunnel test section, authored in OpenUSD and rendered
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
  files with their full absolute paths.

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

PNG/JPEG writes use `tools/image_io.py` (nvImageCodec), including the smoke test and fixed
presentation outputs in `tools/build_media.py`. MP4 uses PyNvVideoCodec with NVENC and its
libav-based muxer; the ffmpeg executable is needed only for `tools/render_motion.py --encode --gif`.
Warp computes periodic spectral noise, material maps and the heavier mesh operations. numpy remains
for array exchange, USD packing and diagnostic checks. Run `tools/check_compute.py` for numerical
and codec regressions. `tools/check_presentation.py` checks authored motion and framing. Motion uses
Warp filtered downsampling with `--supersample 2`; `--res` remains the output size. Optional task
10e is deferred pending dataset acceptance and download approval.

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
