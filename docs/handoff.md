# Handoff

State of the repo as of 2026-10-30, for the next session picking it up cold. Read `CLAUDE.md` first,
then `docs/plan.md`, then this file.

## Where things stand

- Owner feedback: ASCENT is an interesting, higher-quality scene than the earlier result. Camera movement feels too stop-and-go; use smoother transitions in a future presentation pass. The car and field slice feel out of place in the hall story, but are a useful integration test. Keep the cached case private and separate from the main scene narrative. The owner subsequently approved the focused source commit, PR and merge, plus a separate smoother hall-only presentation. The new film stays local until visual acceptance.

- [Issue #5](https://github.com/sushiHex/stagewright/issues/5), milestone 3, tracks the owner-authorized focused source delivery. Final capture and browser
  checks are complete; use the linked PR for current delivery status. The direct harness is implemented: publish creates immutable
  complete USDZ revisions; engine records isolated CUDA physics and exports USD replay; observe owns
  one OVStage/RTX renderer and streams through ovstream to the no-build browser client. Revision
  selection, replay controls and last-good retention passed browser checks. See docs/live-viewer.md.

  Construction trial 001 completed with requested gpt-6-astra / max and context=clean. Its frozen
  starting corpus is unchanged. The constructor built ASCENT, a large proving hall with an original
  vehicle, referenced vault ribs and a three-body lifting entrance. Five actual complete publications
  retain its progression. Revision 0005 is the final recorded solver replay. One angular drive moves
  the undriven canopy and follower through four joints. The no-drive control stays stationary.
  Parent checks of the actual published gate geometry and sampled world matrices support the scoped
  result: about 12.2 m lower-edge height above the nominal datum, with replay agreement within
  floating-point precision. The lane surface is 0.025 m above that datum. This is zero-gravity
  mechanism motion, not structural, contact, loaded-operation or aerodynamic validation.

  Evidence is under ignored build/experiments/transforming-hall-001/. The exact prompt, requested
  settings, pre-run hashes, first-result hashes and all evaluations remain. admission-003/result.json
  retains the full returned Hardline result. actual_model/effective_effort remain null. The returned
  context report records configured clean isolation and observed thread startup, not instruction
  ingestion. The successful response has no execution transcript, so all tool reads cannot be
  independently audited. Keep that limit visible; do not call this a fully audited context trial.

  The first two admissions stopped at Hardline's enforcing MXC preflight. The owner approved a narrow
  fix in the separate Hardline repo: a separate startup allowance, with all policy/canary/pin checks
  retained. Focused checks and an original-defect mutation pass. A fresh MCP process with the same
  registration configuration and a private trial store ran the successful attempt. Its adapter hash
  is retained. The main session's MCP process still runs old code; reconnect before relying on its
  patched behavior. No elevated or unrestricted fallback was used. The temporary driver was stopped
  after result collection. The corrected saved driver handles nested job status for future runs.

  The first physics evaluation hit an unwritable OS temp directory. The constructor recovered on its
  own using workspace scratch space. Root tools/engine.py now supplies worker-local TMPDIR/TEMP/TMP;
  a focused real-child CPU probe verifies the directory and unchanged caller environment. The frozen
  constructor tools remain unchanged. No publisher fix was needed: the nested-package animation probe
  passes. Complex persistent preview accumulation remains a known limitation; final captures retain
  convergence checks. The private capture now applies static pose layers to one renderer/Stage: five
  sampled attributes get strong defaults over the immutable source. Closed, open and reference views
  converge. A parallel capture attempt did not progress reliably and its extra VRAM claim is released.

  The approved private Blueprint cache and mesh match their LFS identities. Historical provider
  source binds that exact pair and configuration, including High ride height, in release 2026.05;
  those identities persist through the frozen source revision. This supports a provider-published
  cached reference, not fresh inference or independent attestation of its original generation.
  Warp SimData derives the actual speed slice and streamlines. Source evidence is retained in
  build/checks/blueprint-source-provenance.json and with the private display assembly.

  build/private/ascent-review/ contains the separate post-construction display assembly. It keeps
  the complete field/mesh group registered, leaves recorded hall coordinates unchanged, disables
  duplicate case cameras/lights, and adds a camera inspection pass. Its publications retain the five
  original package bytes and add private revision 0006. Separate private revision 0007 corrects the camera pass that hid
  the linkage behind a foreground column. The original model camera remains intact. Geometry,
  animation, camera and dependency checks pass. The full-HD loop is complete: decoded first/last
  pixels match, holds are equal and source ordering is symmetric. Browser checks pass for play/pause,
  seeking, loop toggle, recorded clearance and the cached-reference label. The private HTTP preview
  needs byte ranges for Chrome seeking; build/checks/serve_ascent_review.py supplies them. A nearest-
  available-sample scrubber fix avoids jumps to the start. Top-edge shading keeps labels readable
  without panels or text halos. The native observer also shows closed and raised geometry plus the
  reference camera after actual USD time changes. No animation exporter change was needed. Browser
  automation later timed out on review-tab reloads and recovery. A subsequent focused fresh-tab
  check passes explicit disconnect/reconnect, page reload, delivered video and raised-geometry
  seeking against one running observer. No lifecycle code change was needed. This does not explain
  or universally exclude the earlier automation failure. The unverified native contrast CSS
  change was removed, retaining the viewer version used for the successful motion checks. Native
  overlay contrast over dark geometry remains a visual limitation. The private movie page was
  visually checked after its shading fix.
  Keep all protected data and renders private. The live observer was stopped after review and its
  GPU reservation released. The private HTTP movie player remains available. Use a new observer
  session directory and coordinate through vram-mcp before starting it again.

  The polished readiness mini-demo under build/probes/physics/final/ is frozen. Accepted public media
  remain unchanged. Delivery uses a focused source branch and linked PR. Earlier unrelated wind-tunnel candidate
  edits remain intact. The focused PR draft is build/checks/live-harness-pr.md; capture and browser review are complete. The focused worktree
  is C:/Users/kfaim/repos/stagewright-live-harness on branch live-scene-harness. It contains only the
  21 whitelisted source/doc files; no build or external data. Consequential-risk review found no
  blocker. The owner authorized its commit, PR and merge. A separate hall-only continuous camera
  presentation is in progress under build/candidates/ascent-presentation-002; do not include that
  output or the cached reference in this source PR. Avoid more mini-demo polish or new features.

- Hardline [PR #123](https://github.com/sushiHex/hardline-mcp/pull/123) is merged at `2a24ee3`.
  After the owner-authorized configuration edit and restart, server_info verifies code revision
  `2a24ee3b0bbd` and `write_enabled: true`. The write-gate blocker is cleared. It is enabled on the
  shared Codex hardline MCP registration; individual calls still need write=True and workdir.
  Construction uses context="clean" with a frozen workdir containing its own real .git directory.
  Preserve requested_model/requested_effort/actual_model/effective_effort exactly as returned,
  alongside resolution, routing/instruction notes, context report and pre-run workdir digest.
  Null remains unknown. Observed startup is not proof of instruction ingestion; retain residual
  context limits. Claude clean writes remain unsupported. No additional Hardline feature is needed;
  USD publication/rendering stays in Stagewright. These peer reviews are planning, not construction.

- [Issue #4](https://github.com/sushiHex/stagewright/issues/4), milestone Sectional environment
  construction: branch `sectional-housings` adds explicit model-directory destinations to both
  builders, a shared profile/station construction for nozzle and collector exterior jackets,
  and `coarse`/`final` variants on `/Environment/Geometry/Tunnel/Housings`. Candidate outputs live
  under ignored `build/candidates/sectional-housings/`. Existing geometry, lights, textures and
  accepted media are unchanged; both variants have matching bounds and clear the flow domain.
  The validator has only the accepted USDA storage exception. Presentation motion checks and
  a focused check of the new housings against blueprint camera samples pass. Renderer startup
  succeeds again without code or settings changes; the cause of the earlier stall remains
  unconfirmed. Matched Hero/Wake baseline and final-layout renders, final Detail and coarse
  Hero/Detail all completed through RTX. Both native USD variants render: coarse preserves
  the layout and visibly reduces curved detail. The local `comparison.html` contains the
  completed comparisons. Cutaways read most clearly in Detail; the broad collector view is
  subtler. The owner judged this modification too subtle for the intended demonstration;
  set further jacket refinement aside and retain the useful builder/LOD work. Changes remain
  uncommitted; accepted assets and public media are untouched.

- [Issue #3](https://github.com/sushiHex/stagewright/issues/3): an uncommitted scene candidate adds
  one inset turntable marking using the existing Accent material (radii 460..480 cm, top Z 0.20 cm).
  Astra and Fable agreed on the change. Candidate assets and the matched Hero render live under
  ignored `build/candidates/turntable-marking/`. Containment and presentation checks pass; validation
  has only the documented USDA storage exception. Existing environment attributes and textures
  match the baseline. Canonical assets and accepted media remain unchanged pending visual acceptance;
  do not refresh public media from this candidate yet.

- Simplification pass: render CLIs now log output paths directly, without diagnostic-only pixel
  statistics; unused path constants were removed. Focused CPU checks confirm unchanged pixel
  forwarding, output paths, convergence handling and sample settings. No rendering settings changed.

- The shared renderer now rejects unconverged captures before readback; the focused CPU check
  covers successful capture, failure and discarded warmups. One disposable material fixture using
  installed `usdex.rtx.definePbrMaterial` rendered in pinned ovrtx: its red MDL material appeared red
  while its disconnected universal fallback and the PreviewSurface control were blue. The render
  converged without reported errors, supporting MDL execution for this fixture only. Probe files
  remain under ignored `build/probes/mdl/`; production materials and accepted media are unchanged.

- The concise README leads with prompt-based procedural creation and an explicitly scoped NVIDIA
  core pipeline. It includes an original SVG diagram and a linked model technical guide.
  `requirements.txt` centralizes the unchanged dependency pins. Link, package, media-hash and
  Python em-dash checks passed; desktop and narrow layouts were inspected. The owner authorized
  publishing this revision. Accepted media remain unchanged.

- Public repository: [stagewright](https://github.com/sushiHex/stagewright), branch `main`.
  Initial public release commit: `29a3c89`. Public visibility, MIT detection and exact remote-tree
  parity were verified. Protected outputs and dependencies are excluded from the full history.

- Tasks 1 to 8 of `docs/plan.md` are done: the environment builds, validates, passes
  `tools/fit_check.py --strict` (29 checks, 0 FAIL, 0 NOT CHECKED), and renders.
- Task 9 (gsplat backdrop) is not started.
- The repo was renamed from open-jet-test-section to stagewright on 2026-10-27; the wind tunnel is
  its first model. A fresh `.venv` was built at the new path and the rebuild, validation (only the
  accepted array rule fails) and `fit_check.py --strict` (0 FAIL) were re-run there.
- Task 10a to 10c are implemented: nvImageCodec PNG/JPEG, PyNvVideoCodec NVENC H.264 and MP4
  mux, and ffmpeg GIF only behind `--gif`. No Pillow imports remain.
- Task 10d is implemented: Warp spectral textures and mesh kernels. The numerical/codec regression
  script passes. Both port stages pass validation except the accepted USDA array rule and pass the
  strict fit check (29 checks, 0 FAIL, 0 NOT CHECKED). Mesh positions and topology match the saved
  baseline exactly; expanded normals and UVs agree. Honeycomb maps remain pixel-identical.
- Tasks 10a to 10d are DONE, including regenerated final stills, QC and the full dolly. MP4 container
  metadata, uniform timestamps and sampled decoded frames were checked. The public JPEGs and MP4
  were refreshed through `tools/build_media.py` from fixed presentation outputs.
- The owner accepted the Dolly and the revised Orbit360. Both movie hashes and all existing still
  hashes are preserved in the local acceptance record. Keep accepted media unchanged during any
  further optimization trials.
- Orbit360 is revised into a wider dolly/crane tour, changing distance, height and aim to show
  the hall, nozzle, turntable and collector. Authored closure, continuous seam velocity/acceleration,
  body/environment framing and camera clearance checks pass for both roots. The full-quality render,
  repeat-pose, source/decoded seam and timestamp checks passed; public loop media is refreshed.
  Local review/source archives are refreshed with the wider shot and current tools.
  MIT remains applied. This approved state is published to `https://github.com/sushiHex/stagewright`.
  Further changes still require explicit commit authorization.
- Further private profiling identified renderer convergence as the optimization priority. Shared
  still/motion sample batching preserves the explicit sample budget, with a reference option and
  authored-setting preservation. Image acceptance, CPU budget/control tests, production motion
  repeat-pose and source-seam checks pass. The still CLI smoke converged and produced a complete
  PNG. Normal scene updates already propagate sampled properties; a camera-only update path was
  not added. Both render CLIs support `--sample-batch 1` for the reference launch schedule.
- Additional GPU/concurrency trials are unvalidated: larger sample batches and PathTracing-only
  initialization encountered resource-upload failures under current GPU resource pressure. Keep
  the verified defaults. PNG writing is a minor measured stage, so no Python writer thread was
  added. Re-run candidates with adequate GPU headroom before accepting further changes.
- Next-run motion rendering skips warmup readbacks, filters mapped CUDA pixels before the host copy,
  and reuses sequence-owned codecs and filter buffers. Same-frame CPU-reference parity, cleanup and
  ownership tests, optimized motion smoke and numerical/codec/routing regressions pass. Sampling,
  filtering and encoder quality are unchanged; `--cpu-readback` retains the reference path.
- The focused presentation pass is complete: the dolly passes the body, the collector bulkhead
  has fasteners, and motion supports Warp triangle-filtered supersampling with a native fallback.
  Final stills, QC, full dolly and public media are refreshed. MP4 metadata and sampled decoded
  views pass checks. `tools/check_presentation.py` verifies all 216 poses, framing and clearances.
  Fine-pattern shimmer remains a visual acceptance risk; it is not claimed to be eliminated.
- Task 10 is complete against its delivery gates. Optional task 10e is deferred; dataset terms and
  renderer compatibility remain unverified. No dataset was downloaded. Task 11 is complete.
- The initial baseline is commit `227b9e0`; task 11 is isolated from subsequent visual changes. Commit only when the owner asks;
  messages stay neutral (no product names from the hard rules, no AI or process talk, no trailers).

## Rebuild from scratch

```
.venv/Scripts/python.exe tools/build_env.py
.venv/Scripts/python.exe tools/build_present.py
.venv/Scripts/nvidia_usd_validate.exe models/wind_tunnel/assets/test_section.usda
.venv/Scripts/python.exe tools/check_presentation.py
.venv/Scripts/python.exe tools/fit_check.py --strict
.venv/Scripts/python.exe tools/render.py --res 1920x1080 --spp 256 --prefix final_
.venv/Scripts/python.exe tools/render.py --products Main --qc --res 1920x1080 --spp 256 --prefix final_qc_
.venv/Scripts/python.exe tools/render_motion.py --res 1280x720 --spp 64 --supersample 2 --encode
.venv/Scripts/python.exe tools/render_motion.py --product Orbit360 --res 1280x720 --spp 64 --supersample 2 --encode
.venv/Scripts/python.exe tools/check_loop.py
.venv/Scripts/python.exe tools/build_media.py
.venv/Scripts/python.exe tools/build_share.py
.venv/Scripts/python.exe tools/check_compute.py
```

`fit_check.py` and the blueprint render need `external/blueprint` (clone instructions in
`models/wind_tunnel/docs/guide.md`,
pinned commit `62610544f41a338a8abbbe32e2e902d4107c506d`, LFS skipped, CarHero fetched separately).

## Outputs

| Path | What |
|---|---|
| `build/stills/final_{hero,detail,main,wake,qc_main}.png` | finals, 1920x1080, 256 spp |
| `build/stills/*.png` (no prefix) | older 960x540 review passes |
| `build/out/orbit360.mp4` | loopable full dolly/crane tour, with repeat-pose guards kept outside the video |
| `build/out/dolly.mp4` | 216-frame dolly, 1280x720, 64 spp; GIF is optional with `--gif` |
| `models/wind_tunnel/media/*.jpg`, `models/wind_tunnel/media/*.mp4` | fixed presentation copies for README; GIF generation is optional and not copied by default |
| `build/share/stagewright-{review,source}.zip` | local verified review/source archives, with offline player and checksums |
| `build/private/*.png` | renders containing the blueprint's own car. **Never publish, never commit, never copy into public media** |

## Next steps, in order

The render-harness increment is tracked in [Issue #1](https://github.com/sushiHex/stagewright/issues/1), under the
[Lean render harness milestone](https://github.com/sushiHex/stagewright/milestone/1).
Use linked PRs for changes and close their Issues through the implementation PR merge.

**SIMPLIFICATION IS PROGRESS.** The MVP is established. Keep the project a light, direct harness
for the NVIDIA core pipeline, with YAGNI over TDD. The adversarial review does not authorize a
validation framework, render manifests, compliance layers or an expanded test program. The local
convergence fix and bounded MDL probe are complete. No material migration follows automatically.
Further infrastructure or integrations need a concrete use; they are not automatic next tasks.

1. The approved public release is `https://github.com/sushiHex/stagewright`, with `main` as the
   release branch. Preserve both accepted movies and existing still hashes. Further optimization
   stays separate from this release; verified render settings remain active. Commit further changes
   only when requested.
2. Keep fine-pattern shimmer documented as a known limitation. Revisit presentation changes only
   when requested; acceptance does not establish universal shimmer removal.
3. Optional task 10e remains deferred. Revisit only after terms acceptance and explicit download
   approval, with one renderer compatibility trial before any migration.

The wind tunnel lives under `models/wind_tunnel/{assets,scenes,docs,media}`. Root `docs/` holds
project planning; shared tools remain in `tools/`. Build outputs, private renders and the external
blueprint clone remain at the repository root. Layout verification passed: exact rebuilt asset,
texture and presentation-layer parity, resolved local dependencies, documented validator exceptions
only, strict fit 29 checks with none failed/unchecked, and a visually equivalent reference hero.
Pixel identity is not claimed across stochastic path-tracing runs. The local private root's
sublayer path was updated without rendering or copying its images.

## Implementation notes

- `.gitattributes` keeps ASCII USD files at LF so verified scene hashes survive Windows checkouts.

- `tools/check_compute.py` checks the Warp spectral implementation against a Fourier reference,
  analytic mesh cases, lossless PNG, JPEG and MP4 color/frame ordering. Fixtures stay in `build/`.
- Only complete canonical motion sequences can write their built-in `build/out/` videos; custom
  and preview videos stay with their explicit frame directories, away from fixed public media sources.
- `tools/build_share.py` uses explicit first-party paths and rejects protected roots and stale loop
  verification. Archives exclude private renders, the external blueprint, dependencies and build logs.
- PyNvVideoCodec's packed RGB path produced full-range YUV without range metadata in this pinned
  build. `tools/video_pixels.py` computes limited-range BT.601 NV12 explicitly in Warp.
- `tools/video_io.py` drains encoder packets, uses a 90 kHz clock and disables B-frames for direct
  monotonic timestamps. Its muxer is libav-based. No ffmpeg executable is needed for MP4.
- Warp's seeded noise generator changes the noise patterns while preserving periodic spectra.
  The saved previous assets and scenes are in gitignored `build/baseline/` for local comparisons.
- README and CLAUDE.md use `requirements.txt`; the technical guide records the same install pins.
  Public docs contain no render durations or other
  performance figures. Python text checks found no em dashes.

## Known weaknesses (presentation)

- The Ahmed body reads as a box at some angles.
- Honeycomb fine-pattern shimmer remains an acceptance risk. Motion has a Warp triangle-filtered
  supersampling option, with native sampling retained. Do not claim every view is shimmer-free.
- Collector geometry remains simplified; its bolted bulkhead now adds mounting detail.

## Decisions waiting on the owner

1. SimReady materials: accept the gated dataset terms (task 10e).
2. DrivAerML body (CC-BY-SA) to replace or join the Ahmed body: a download, needs approval.
3. Phone capture of a large interior for the gsplat backdrop (task 9).
4. Licence is resolved: MIT for original code and generated content; dependencies keep their terms.
5. Repository name and public release are resolved: `sushiHex/stagewright`.
6. Blender MCP: not installed; current direction is code-only.
