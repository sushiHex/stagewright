# Build plan

**SIMPLIFICATION IS PROGRESS.** Keep a light, direct harness for the NVIDIA core pipeline.
YAGNI takes precedence over TDD. Review findings are candidates, not an automatic backlog:
fix concrete failures with small local changes and use only the checks needed to prove them.
Render manifests, validation orchestration, broad CI/support matrices and material migrations
are not planned requirements. Expand only for a demonstrated use. See `CLAUDE.md`.

## Finalized experiment: the transforming proving hall

The final Fable -> Astra -> Fable -> Astra exchange agrees on one story:
**prompt -> live USD construction -> useful physical transformation -> matched Blueprint analysis.**
State-of-the-art ambition belongs in the result, not in a larger harness. The constructor chooses
an extraordinary facility and feasible mechanism; Stagewright connects existing libraries directly.

### Creative brief and visual story

Create a monumental automotive proving hall whose architecture reconfigures to change its useful
access, clearance or enclosure. One driven input causes mechanically dependent architectural motion
through simulated constraints. A hall opening into a courtyard is art direction, not a linkage recipe.
Keep the vehicle as a scale reference. The change must read in a wide view and alter usable space;
small cosmetic changes or movement of an incidental prop do not satisfy this experiment.

The visual story moves from an establishing wide view, to a close view showing the drive and its
physical dependency, then back to the transformed space. Camera animation supplies presentation;
recorded solver motion supplies the physical evidence. During construction, show actual complete
saves when the constructor publishes them. No imposed artistic phases or invented intermediate
states. An authored assembly reveal is labelled presentation, not construction history. A single
final save demonstrates final delivery but does not establish live build progression.

Use terminal-style text directly over the video, without HUD panels. Keep the cool neutral
structure, orange driven elements and blue dependent motion. Use ASD-STE100 writing rules for page
text and consistent technical names. The current HUD uses dark text, larger readings and one result
line. Labels and units use high contrast against the light image. Keep the moving parts clear of text.
Show selected recorded values with replay/live state explicit.
Translucent arm silhouettes use the USD camera, geometry and recorded poses. Warp composites them
into the matching video frames to prevent browser overlay drift. They replace the broken native
hidden-edge effect in the local probe. The video uses full-HD RTX frames. The loop
samples recorded bridge travel, with equal holds at both ends and identical decoded end images.
The timeline shows both directions without status labels; the return is not a second simulated operation. The HUD returns
to the same data sample at the boundary. The centered readouts use animated angle arcs and a vertical lift indicator, with exact numbers.
Fixed readout columns prevent digit changes from moving the graphics. Smaller numbers sit close
to each graph, and the group sits higher in frame. Playback uses a play/pause icon and a thin
progress track with an orange forward state and blue return state.
They remain an HTML/SVG overlay; the outlines
are in the MP4. The lower slider moves at a constant rate forward and backward with the replay. This does not establish a live backend. Reuse this presentation direction in the planned live window.

The readiness rig has presentation-only rounded links, clevis mounts, washers and pivot pins over
its immutable replay. The look layer retains source stage metadata. Recorded body motion and
physics properties remain unchanged; the decorative hardware is not a new simulation result.

The constructor may use one declared engine CLI, inspect its measured output and revise its design.
State an observable useful-operation condition before execution. Preserve the initial candidate,
evaluated revisions and exact feedback consumed; do not require a failure, repair or second design.
Human visual acceptance and the recorded operation determine success, not the agent's own assertion.
Rigid-body mechanism behavior does not establish structural adequacy or environmental performance.

### The smallest harness

- **Author and publish:** existing usdex/pxr functions in a frozen constructor workdir. One optional
  declared helper publishes an immutable complete USD root with retained relative dependencies, then
  advances one revision pointer. The constructor decides when to publish during its continuing session.
  A pointer alone cannot make half-written assets safe. Results go outside published input revisions.
- **Execute:** one separate ovphysx worker behind the engine CLI, used for headless runs and preview.
  Record poses and only the joint/drive/contact observations actually available or explicitly computed.
  Preview and exported USD replay use the same recorded samples. Missing required export is a partial
  result, not a reason to simulate again just for presentation. Keep prescribed input distinct from
  solver-owned motion. Hinges alone do not prove coordinated motion; resolve constraint feasibility.
- **Observe:** one renderer owner, ovstage/ovrtx -> ovstream -> small no-build browser client.
  Show the exact prompt, configured model/effort, saved revision and status. Revision selection is
  separate from the USD playhead. Keep the last good revision identified after failure. Saved replay
  is labelled. Viewer cameras and reversible display state stay outside source USD. No full editor,
  new chat backend or constructor coaching channel. Retain final-capture convergence behavior.

Follow [NVIDIA's viewer guidance](https://github.com/NVIDIA/skills/blob/main/skills/omniverse-realtime-viewer/SKILL.md).
The [maintained Web SDK sample](https://docs.omniverse.nvidia.com/ov-web-sdk/latest/web-sample/overview.html)
supports TypeScript without React but targets Kit; a compatible standalone client must be proved.
A disposable no-download JPEG publication probe may precede streaming, then is retired. Keep the
existing author/renderer boundary and separate physics process. Runtime ordinals are not saved
revision history; retain actual USD revisions. No new transport, publication manager or orchestrator.

Use `CLAUDE.md` for clean construction, frozen inputs and the existing run record. Preserve the returned
`requested_model`, `requested_effort`, `actual_model`, `effective_effort`, resolution, context/routing
notes and workdir digest exactly. Null remains unknown, not a blocker. Peer planning is outside the
constructor's context except the selected frozen brief and tool reference. Adapt the reasoning/tool/
feedback pattern of [USD Content Agents](https://github.com/NVIDIA-Omniverse/usd-content-agents), not its stack.

### Two delivery gates, one issue

1. **Live transforming hall:** show meaningful completed USD saves during the constructor session,
   a scene-wide useful transformation caused by the solver, and an inspectable stage plus recorded
   replay. No manufactured history or mandatory redesign. Export the actual story with existing NVENC
   tools. Use a public-safe authored vehicle; keep accepted media unchanged until a replacement is accepted.
2. **Matched Blueprint result:** show one permitted actual scientific result in the same application
   window, tied to matching geometry identity, inference parameters, case and source revision. This
   follows the grand physics demonstration and is required for full Issue #5 completion, not optional
   forever. Mere Blueprint scene composition does not satisfy the results gate.

For every prompt, expose its actual scene revision and result availability: pending, cached, fresh
or unavailable, with source case/revision identified. Keep an older result labelled as older. A prompt
that changes unsupported geometry gets unavailable analysis, not a borrowed field. Our existing
override composes and renders; full Blueprint application loading and inference have not run.

The [Blueprint developer guide](https://github.com/NVIDIA-Omniverse-blueprints/digital-twins-for-fluid-simulation/blob/main/docs/developer-guide.md)
uses matched result revisions for visualization and streaming. The owner-approved NanoVDB case and
mesh are now downloaded and hash-verified. Warp SimData -> ordinary derived USD -> the same renderer
is implemented and displayed. Source history associates this exact pair with the provider's bundled
configuration. Retain the cached-reference scope and the original source evidence. No second
streaming backend or speculative parser is needed.
Kit root loading and client compatibility remain unproved; default_stage metadata is insufficient.

Cached tracer animation is visualization of a steady field, not a transient solve or new inference.
The [NVIDIA CAE blueprint article](https://developer.nvidia.com/blog/rapidly-create-real-time-physics-digital-twins-with-nvidia-omniverse-blueprints/)
explains the design/simulation/visualization loop and limited-geometry surrogate context. A changed
hall does not establish new aerodynamic predictions. Never replace a field's vehicle geometry with
the public prop. Protected car views remain under `build/private/`, excluded from public capture.

### Useful reuse, without a library collection

| Use | Reuse and boundary |
|---|---|
| Procedural environment | Existing OpenUSD Exchange, Warp geometry/textures and codecs. Native references/instances for useful repetition; independent mechanical bodies remain identifiable. Retain useful coarse/final variants, not an automatic distance-LOD claim. |
| Operable architecture | OpenUSD UsdPhysics joints/drives plus ovphysx and registered external PhysX schemas. Prove actual backend support; collect contacts only if the chosen operation needs them. |
| Live result | Existing ovstage/ovrtx and compatible ovstream client. One owner for stage lifetime, updates and rendering; no browser USD renderer. |
| Matched CAE case | NVIDIA Warp SimData for supported field processing, not a solver. Use CAE OpenUSD Plugins/Kit only when the actual case requires them. Keep conflicting Python/USD runtimes isolated. |

Apply [NVIDIA asset principles](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html)
through existing usdex helpers: stable lightweight interfaces, reusable referenced components, heavy
content behind payloads where useful, and computed layers over retained source. No fixed layer count,
scene taxonomy, asset catalog or instancing rewrite. Purpose is not automatic LOD.

[ovphysx](https://github.com/NVIDIA-Omniverse/PhysX/tree/main/ovphysx) and
[Warp SimData](https://github.com/NVIDIA/warp-simdata) have open-source implementations; prebuilt
ovphysx wheels and ovrtx/ovstream retain NVIDIA runtime terms. Do not call the entire runtime open
source. The construction model and Python orchestration remain outside the NVIDIA core scene claim.
Defer BRep, FEA, fresh CFD for arbitrary prompts, broad material migration, collection overlays and
new optimization/agent frameworks. Appearance does not supply physical properties. Warp installation
does not differentiate PhysX. No speculative validation program.

### Implementation progress and next steps

1. **Readiness reference frozen.** GPU physics, recorded USD replay, RTX capture and NVENC output
   are proven for the zero-gravity mechanism. The local looping reference is complete. Keep it fixed.
2. **Live observer implemented.** The direct publisher creates immutable complete USD packages.
   One OVStage/RTX owner streams through ovstream to a small no-build NVIDIA browser client.
   Browser checks cover two distinct revisions, independent playback and last-good retention.
   Persistent animated CUDA capture passes on the minimal fixture. Complex preview accumulation
   remains distinct from final capture, whose convergence requirement stays intact.
3. **Grand construction and playback review completed.** Trial 001 used the unchanged
   frozen corpus, requested gpt-6-astra / max and clean context. The constructor produced ASCENT,
   retained its evaluated revisions and published the actual solver replay. One input drives the
   dependent architecture; the no-drive control stays stationary. Published gate geometry clears
   the stated opening condition and replay matrices agree within floating-point precision. Keep
   zero-gravity mechanism scope explicit. Served model/effort remain unknown; the returned context
   report proves startup, not instruction ingestion, and no execution transcript was returned.
4. **Private provider reference composed.** The approved cache and mesh match provider LFS identities
   and the original release's case binding. Warp SimData derives a speed slice and streamlines.
   A separate private display assembly preserves their common transform beside the unchanged hall
   replay and adds a camera inspection pass. This is a provider cached reference, not fresh inference
   or hall CFD. Original generation-session and checkpoint digests remain unknown. The full-HD loop passes
   decoded endpoint equality, equal holds and symmetric source ordering. Browser playback, seeking
   and controls pass. Native USD time changes also show the closed gate, raised gate and reference
   camera. A fresh-tab disconnect/reconnect and page reload also pass against the same running
   observer. No lifecycle code change was needed. Keep protected data and renders under build/private.
   The owner approved the focused source delivery; the separate smoother hall-only film stays local
   until visual acceptance.


See docs/live-viewer.md for setup and use. Keep private data, results and frozen construction records
under ignored build/. The owner authorized the focused source commit, PR and merge, plus a separate
hall-only camera presentation. Keep delivery status in Issue #5 and its linked PR. Preserve earlier
unrelated candidate edits and accepted public media. GPU work requires vram-mcp coordination. Do not publish
render times or performance figures. Track active work in existing Issue #5 and milestone 3.

## Delivered baseline

Status as of 2026-10-27 (handoff notes in `docs/handoff.md`; tasks 10 and 11 are complete; task 13 adds a loop shot and prepares sharing):

- **Done:**
  - The ovrtx smoke render works on the RTX 3090 (lit, shadowed, PathTracing).
  - The blueprint is cloned to `external/blueprint` with LFS skipped.
  - The NVIDIA authoring and validation packages are installed.
- **Done:** the blueprint's own stage (their `Main.usda` plus our override, CarHero geometry fetched)
  loads and renders in ovrtx from their CameraMAIN_00, with their car standing centred on our
  turntable. That render is a private check: it shows their car, so it stays in the gitignored
  `build/private/` and is never published.
- **Done:** camera animation through time samples works. The earlier "same pose" result came from a
  symmetric test scene (see "Camera motion" in CLAUDE.md).

## What we are making

A replacement for the blueprint's wind tunnel environment: a full-scale **open-jet, three-quarter
test section** in a plenum hall. It has a floor with a rolling road and a turntable, a nozzle
upstream, and a collector downstream. There are no walls or ceiling around the car itself; the jet is
open. It drops into the blueprint through one override layer. The repo also ships a presentation root
with an Ahmed reference body, a lighting QC set, cameras and render products.

**Deliverables:**

- an MP4 (dolly or orbit)
- an optional GIF thumbnail (`--gif`)
- three stills: the hero shot, the blueprint's CameraMAIN_00 view, and a detail shot
- a QC still
- the fit-check output
- a README

## NVIDIA tooling map (the narrative)

| Stage | Tool | Status |
|---|---|---|
| Author geometry, materials, lights | **OpenUSD Exchange SDK** (`usd-exchange` 3.0.1, `usdex.core`), its bundled OpenUSD 26.8 | installed |
| Scene contract | the blueprint's own stage (`external/blueprint/.../auto-aero/stages`) | cloned |
| Validate | **NVIDIA USD validator** (`usd-validation-nvidia` 1.22.0, `nvidia_usd_validate`) | installed |
| Render | **ovrtx** 0.6.0 / **ovstage** 0.3.0, headless RTX PathTracing | working |
| Splat backdrop (stretch) | **3DGUT** (`nv-tlabs/3dgrut`) to train, then **usd-convert-gsplat** to UsdVol ParticleField, rendered by ovrtx | not started |
| Procedural textures and mesh computation | **Warp** 1.18.0 | implemented, numerical and fit gates pass |
| PNG/JPEG | **nvImageCodec** 0.9.0.20 | implemented, lossless PNG round trip checked |
| MP4 | **PyNvVideoCodec** 2.2.3 (NVENC encode and MP4 mux) | implemented, color and frame order checked |
| Materials (optional) | PhysicalAI-SimReady-Materials (MaterialX) | gated, terms not accepted |

Non-NVIDIA tools: ffmpeg only for the optional `--gif` fallback. Blender is optional, through `mcp-for-blender`, and is not
installed. If it is used, it is for hand-detailing only, since its add-on runs arbitrary Python and has
telemetry on by default.

Geometry in this harness is parametric Python through usdex. STEP import is not implemented.

## Geometry spec (centimetres, Z-up; flow runs along world -Y)

- **The flow domain must sit fully inside the jet** (X -144..144, Y -650..430, Z -4..248).
- **Nozzle:**
  - exit about 650 wide by 400 tall (about 26 m2)
  - exit plane at Y +775 (moved from the nominal +700 so two blueprint camera paths stay 35 cm clear of the lip; see models/wind_tunnel/docs/fit-check.md)
  - contraction body extending upstream to Y +1575, supported by side A-frames and one portal at the settling chamber
  - honeycomb or screen visible through the exit, as one mesh or a normal-mapped plane
- **Collector:** a bell-mouth intake about 800 by 500 at Y -1100, with the diffuser receding beyond it.
- **Floor:**
  - top at Z 0, the domain floor at Z -4
  - a rolling-road belt about 100 wide under the car, running along Y, kept on the turntable (Y -321..507)
  - four wheel-drive belt units (35 x 60, flush, steel frame) under the blueprint car's tyre contact patches, making a five-belt layout; fixed at that car's track and wheelbase
  - a turntable about 1000 in diameter, centred on the blueprint car's mid-wheelbase (Y 93, from the fit check)
  - a painted centreline
- **Plenum hall:** about 2400 wide, 3300 long (Y -1600..1700) and 1200 high.
  - walls: perforated or acoustic panels
  - ceiling: light panels, each with a RectLight behind it
  - fill: a low-intensity DomeLight
- **Look:**
  - chamfered edges, inset panel seams and flanges
  - neutral greys plus one accent, never green
  - 4 or 5 materials with roughness variation
- **Ahmed body** (presentation root only):
  - 104.4 long, 38.9 wide, 28.8 high, with a 25 degree slant and nose radius 10
  - 5 clearance on four posts
  - dimensions checked against restatements of the primary source; see models/wind_tunnel/docs/assets.md for what is and is not settled
- **QC set:** grey, chrome and paint spheres at the car position.
- **Naming:** the payload root is `/Environment` with an identity xform. Lights live under it, and so
  does everything else.

## Tasks (each one is a self-contained handoff)

1. **Camera animation fix.** Done 2026-10-26: it was never a renderer bug, see CLAUDE.md "Camera
   motion".
2. **`tools/build_env.py` to `models/wind_tunnel/assets/test_section.usda`.**
   - Build the parametric graybox through usdex, with every dimension in one config block at the top.
   - Done when it validates cleanly with `nvidia_usd_validate` and the domain is inside the jet with
     clearance.
3. **`tools/build_present.py` to `models/wind_tunnel/scenes/present.usda`.**
   - It references the environment and adds the Ahmed body, the QC spheres, the hero and detail
     cameras, and the RenderProducts.
   - Done when it renders non-black from every camera.
4. **Override and fit check.**
   - `models/wind_tunnel/scenes/blueprint_override.usda`: sublayer the blueprint `Main.usda` and apply the explicit
     payload list-op (see CLAUDE.md).
   - `tools/fit_check.py`:
     - Use `XformCache` and `BBoxCache` to check that the environment fully contains the domain, and
       report the clearances.
     - Report any blueprint prim path that addresses something inside the old environment (grep the
       blueprint source).
     - Optionally pull only the CarHero LFS object, to check the car's bounds against the floor and
       turntable.
   - Output a markdown report in `models/wind_tunnel/docs/fit-check.md`.
5. **`tools/render.py`.**
   - Stills at 64 spp for review and 256 to 512 spp for finals.
   - Also render from the blueprint's CameraMAIN_00 with the domain shown as a BasisCurves ghost.
6. **Look development:** materials, seams, light panels, exposure. Every CC0 texture gets an entry in
   `models/wind_tunnel/docs/assets.md`.
7. **Motion:** DONE 2026-10-26; task 10 replaces its image writes and MP4 path.
   - 216-frame Dolly, `build/out/dolly.mp4`; optional palette GIF only with `--gif`.
8. **README:** DONE 2026-10-26 (licence selected: MIT).
   - what it is (a conceptual presentation environment) and what was verified
   - how to use the override
   - the toolchain
   - asset licences
   - no performance numbers
9. **Stretch, gsplat:** see below.
10. **All-NVIDIA pipeline** (owner request, 2026-10-26). Tasks 10a to 10d DONE
    2026-10-27, including regenerated finals, QC, full dolly and public media. Task 10 is complete against its delivery gates; optional task 10e is deferred.
    - **Pinned packages:** `pynvvideocodec==2.2.3`,
      `nvidia-nvimgcodec-cu12[all]==0.9.0.20`, `warp-lang==1.18.0`.
    - **10a. Image writes: DONE.** `tools/image_io.py` uses nvImageCodec for PNG/JPEG.
      Stills, motion, smoke and fixed public media paths use it. PNG round trips are bit-exact;
      a hero re-render was compared with the previous final. JPEG quality is set explicitly.
    - **10b. MP4: DONE.** `tools/video_io.py` uses PyNvVideoCodec NVENC H.264 and its
      libav-based `FFmpegMuxer`, without an ffmpeg subprocess. Encoder output is drained and
      timestamps use an explicit 90 kHz clock with B-frames disabled. Output is replaced only
      after successful finalization. A synthetic clip checks color, frame count and ordering.
      The packed RGB input path produced full-range YUV without range metadata in the pinned
      build; `tools/video_pixels.py` instead computes limited-range BT.601 NV12 in Warp.
      API references: [encoding guide](https://docs.nvidia.com/video-technologies/pynvvideocodec/pynvc-api-prog-guide/using_pynvvideocodec_apis.html)
      and the installed 2.2.3 muxer constructor/method docstrings. No example scripts were copied.
    - **10c. GIF: DONE.** The ffmpeg palette path runs only with `--encode --gif`.
      PNG, JPEG and MP4 are the deliverables; the README embeds stills and links the MP4.
    - **10d. Compute: DONE.** `tools/texture_compute.py`
      computes periodic spectral noise, perforations, honeycomb, floor seams, belt grooves,
      normals and ORM maps in Warp. The radix-two spectral implementation matches an independent
      Fourier reference; its seeded noise patterns differ from the former numpy generator.
      Honeycomb maps remain pixel-identical. `tools/mesh_compute.py` computes profiles, loft
      topology, sweeps, circular parts, resampling, corner normals and box UVs. Mesh positions,
      topology, expanded normals and UVs match the saved baseline. numpy remains for array
      exchange, indexed USD packing and diagnostic checks; lightweight Python controls assembly.
      Both texture and mesh builds pass the validator except the accepted USDA array rule, and
      `fit_check.py --strict` reports 29 checks, 0 FAIL and 0 NOT CHECKED after each port.
      Final stills and QC were re-rendered at 1920x1080, 256 spp, and the full 216-frame dolly at
      1280x720, 64 spp. The MP4 container, uniform timestamps and sampled decoded frames were
      checked against the source PNGs. Public media was refreshed only from presentation outputs.
      `tools/check_compute.py` checks the numerical and codec regressions under `build/checks/`.
    - **10e (deferred, optional). Materials: procedural to NVIDIA SimReady materials** (OpenPBR /
      MaterialX). The Hugging Face dataset `nvidia/PhysicalAI-SimReady-Materials` is gated (HTTP 401),
      so its licence is unknown until the owner accepts the terms. No dataset was downloaded.
      One installed usdex MDL helper fixture rendered successfully in pinned ovrtx; broader MDL
      and OpenPBR graphs remain unverified. Test the actual material before porting. Ask before
      any unpinned download.
    - **Done when (task 10):** README toolchain table names an NVIDIA tool for every stage,
      the install lines in CLAUDE.md and README match, finals and the dolly are re-rendered
      through the new path, and ffmpeg is no longer required unless `--gif` is passed.
      These gates pass. Optional task 10e is deferred and does not block task 11; dataset terms
      acceptance and download approval remain unconfirmed.
11. **Multi-model layout: DONE 2026-10-27.** The wind tunnel now lives under
    `models/wind_tunnel/{assets,scenes,docs,media}`. Project planning stays in root `docs/`, and
    builders/shared helpers stay in `tools/`. `tools/project_paths.py` defines the default model
    location without a model registry or plugin framework. Build outputs and the external blueprint
    clone stay at the repository root. The moved override uses the corrected blueprint sublayer;
    its explicit environment payload and relative texture arcs are unchanged.
    - Rebuilt asset and texture bytes and both presentation layers match the baseline exactly.
    - Local dependencies resolve, validation has only the documented exceptions, and strict fit
      reports 29 checks, 0 FAIL, 0 NOT CHECKED. The reference hero remains visually equivalent;
      repeated path tracing introduces small pixel variation, so pixel identity is not claimed.
    - Motion rendering accepts scene, product, fps and count explicitly. Custom scenes require
      separate output directories; only the canonical default sequence writes the public-source
      dolly MP4. This prevents private/custom scene renders entering the fixed media copy path.
12. **Focused presentation refinement: DONE 2026-10-27, with visual limits.** The dolly now
    travels from behind the tail to beyond the nose, with the body framed throughout. The new
    `tools/check_presentation.py` checks actual sample timing, positions, aim, world-up, framing,
    travel and existing gprim/stilt clearances. No between-sample sweep or occlusion claim is made.
    The collector bulkhead adds matching washer/hex-head fasteners using the nozzle hardware helper;
    the existing nozzle hardware, body shape and stage contract are preserved.
    - Motion offers native sampling (`--supersample 1`) and a default 2x render with a Warp triangle
      prefilter/downsample (`--supersample 2`). The output dimensions are still set by `--res`.
      Independent numerical tests cover the filter. Matched adjacent-frame trials informed the
      choice; the original material is retained. Fine-pattern shimmer remains a visual acceptance
      risk, not a solved or universally eliminated artifact.
    - Rebuilt geometry passes strict fit with 29 checks, none failed/unchecked, and validation has
      only the documented exceptions. Camera framing/travel/clearance checks pass all 216 poses.
    - Final stills, QC and the complete filtered dolly were regenerated. Container timestamps,
      dimensions and frame count pass; sampled decoded views match source PNGs and show the new
      pass beyond the nose. Public JPEG/MP4 copies were refreshed from fixed presentation paths.
      Source and output routing received independent review. No additional assets were downloaded.

13. **Loop shot, MIT and sharing: DONE 2026-10-27.** Preserved the accepted Dolly and all existing
    stills. Added an initial `Orbit360` circular camera path, one full turn,
    exact authored closure and no duplicate endpoint in the encoded video. Framing, actual authored
    poses, uniform cyclic stepping and conservative camera-position clearance checks passed.
    Post-cycle guard poses and the source/decoded seam and container timestamps were verified.
    Applied MIT to original code and generated content, leaving dependency terms intact. Prepared
    explicit-whitelist local review/source archives with an offline looping player and checksums;
    no private outputs, dependencies, downloads, uploads or publication. Leave changes uncommitted
    until requested. Full source/decoded seam, repeated-pose and uniform timestamp checks passed.
    Accepted Dolly/still media hashes are unchanged. Local archives contain checksums and passed
    integrity, privacy and offline-link checks; nothing was uploaded.

14. **Render pipeline reuse: DONE 2026-10-27.** The completed orbit was isolated from next-run
    changes. Sampling, the exact integer triangle filter, encoder settings, motion cadence and output
    routing are preserved. Discarded warmup poses skip readback; sequence-owned codecs and scratch
    buffers are reused; mapped CUDA pixels are filtered before the RGB host copy. `--cpu-readback`
    keeps the explicit CPU reference path. Same-frame captures matched exactly across orbit views.
    Ownership, resizing, cleanup and warmup scheduling checks passed, including launch, conversion,
    readback and interruption failures. The optimized motion smoke test and numerical, codec and
    routing regressions passed. No public performance figures or quality reductions.

15. **Loop framing revision: DONE 2026-10-27.** Replace the tight circular shot with a wider
    dolly/crane tour, using the accepted Dolly as the composition and movement reference. The closed
    cubic B-spline changes distance, height and aim through a low wake-side approach, a rising nozzle
    sweep, a collector establishing view and an opposite-side return. Preserve one complete turn,
    moving loop closure and the accepted Dolly/still media. Check body framing, environment context,
    nozzle/collector establishing views, camera clearance and continuous seam velocity/acceleration.
    Preview views and both authored-root checks passed. Independent review confirmed all existing
    opinions outside the revised camera are unchanged. The full-quality render and source/decoded
    seam, repeated-pose and timestamp checks passed. Public loop media is refreshed; accepted Dolly
    and still hashes are unchanged. Local archives are refreshed with the wider shot and tools.
    No downloads, commits or publication. The owner accepted the revised Orbit360. Its verified
    movie hash joins the existing accepted-media record; further optimization must preserve it.

16. **Offline path-tracing batches: DONE 2026-10-27.** Private component profiling identified renderer
    convergence as the next optimization priority. Ordinary scene updates already propagate only
    time-sampled properties; no camera-only update path was added. Use the documented RTX
    `samplesPerIteration` setting while retaining the total `samplesPerPixel` budget. Shared still
    and motion controls select a batch divisor of the explicit budget and preserve authored settings
    for stills `--spp 0`. `--sample-batch 1` retains the reference launch schedule. Private batching
    trials passed converged accumulation and source-image acceptance. Budget/control tests and
    independent API/source review passed. Production motion repeat-pose stability and source seam
    checks passed. The still CLI smoke also converged and produced a complete PNG. Local archives
    are refreshed with the verified wider loop and current tools. No timings, benchmark figures,
    downloads, commits or publication.

17. **Further GPU and concurrency trials: awaiting clean validation.** PNG output is a minor stage
    in the private component profile; a Python writer thread was not added. Larger sample batches
    and PathTracing-only initialization are documented candidates, but resource-upload failures
    prevented clean comparisons under current GPU resource pressure. Keep the verified batch and
    default mode availability. Re-run the candidates with adequate GPU headroom before changing
    defaults. No quality reductions, new dependencies, watchdog changes or published figures.

18. **Public release: DONE 2026-10-27.** Published the approved MIT-licensed presentation and
    tools to `https://github.com/sushiHex/stagewright` on `main`. Audit the complete reachable history
    and final tree, preserve accepted media hashes, and exclude build outputs, private renders,
    profiling records, dependencies, external assets, secrets and restricted context. Commit messages
    remain neutral with no trailers. Verify the remote commit, public visibility and repository
    contents after push. Public visibility, MIT detection, exact remote-tree parity and the initial
    release commit `29a3c89` were verified. Further optimization remains separate from this release.

19. **README landing page: DONE 2026-10-27.** Lead with prompt-based procedural environments
    and an explicitly scoped NVIDIA core scene pipeline. Use the accepted hero and films plus an
    original SVG pipeline visual. Keep the root README concise and preserve integration, validation,
    render options and provenance in `models/wind_tunnel/docs/guide.md`. Centralize the unchanged
    dependency pins in `requirements.txt`; keep the offline share packages complete. Editorial and
    technical reviews, local link/anchor checks, offline archive checks, media hashes, SVG structure
    and desktop/narrow previews passed. The owner authorized publication. Accepted media and scene
    data are unchanged.

**Gate:** if task 6 has no presentable still five hours into the build, ship stills only.

## Gsplat option

ovrtx 0.6 renders `UsdVol.ParticleField3DGaussianSplat`.

How splats behave in ovrtx:

- Scene meshes cast shadows onto splats.
- Splats are not lit by scene lights.
- They are treated as display-referred, so meshes and splats grade differently.

Two problems:

- `usd-convert-gsplat` needs Python 3.12 or older, so it needs a separate venv.
- No licence-clean capture of an industrial interior was found.

**The strong version is our own capture:** a phone video of a large interior, trained with NVIDIA's
3DGUT on the 3090, converted to ParticleField, and placed beyond the plenum walls as the backdrop, with
the mesh hardware in front. Only attempt it after task 6 passes.

## Research trail

The source notes and reviews are kept outside this repo.
