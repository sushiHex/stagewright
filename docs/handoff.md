# Handoff

State of the repo as of 2026-10-27, for the next session picking it up cold. Read `CLAUDE.md` first,
then `docs/plan.md`, then this file.

## Where things stand

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
- Task 10 is complete against its delivery gates. Optional task 10e is deferred; dataset terms and
  renderer compatibility remain unverified. No dataset was downloaded. Task 11 is next.
- A baseline is captured in repository history before task 11. Commit only when the owner asks;
  messages stay neutral (no product names from the hard rules, no AI or process talk, no trailers).

## Rebuild from scratch

```
.venv/Scripts/python.exe tools/build_env.py
.venv/Scripts/python.exe tools/build_present.py
.venv/Scripts/nvidia_usd_validate.exe assets/test_section.usda
.venv/Scripts/python.exe tools/fit_check.py --strict
.venv/Scripts/python.exe tools/render.py --res 1920x1080 --spp 256 --prefix final_
.venv/Scripts/python.exe tools/render.py --products Main --qc --res 1920x1080 --spp 256 --prefix final_qc_
.venv/Scripts/python.exe tools/render_motion.py --res 1280x720 --spp 64 --encode
.venv/Scripts/python.exe tools/build_media.py
.venv/Scripts/python.exe tools/check_compute.py
```

`fit_check.py` and the blueprint render need `external/blueprint` (clone instructions in README.md,
pinned commit `62610544f41a338a8abbbe32e2e902d4107c506d`, LFS skipped, CarHero fetched separately).

## Outputs

| Path | What |
|---|---|
| `build/stills/final_{hero,detail,main,wake,qc_main}.png` | finals, 1920x1080, 256 spp |
| `build/stills/*.png` (no prefix) | older 960x540 review passes |
| `build/out/dolly.mp4` | 216-frame dolly, 1280x720, 64 spp; GIF is optional with `--gif` |
| `media/*.jpg`, `media/dolly.mp4` | fixed presentation copies for README; the older GIF is no longer embedded |
| `build/private/*.png` | renders containing the blueprint's own car. **Never publish, never commit, never copy into `media/`** |

## Next steps, in order

1. Task 11: isolate the wind-tunnel assets, scenes and model documentation, preserving the current
   visuals and blueprint contract. Validate, run the strict fit check and compare a reference still.
2. A focused presentation pass: make the dolly travel past the body and reduce honeycomb shimmer.
3. Optional task 10e remains deferred. Revisit only after terms acceptance and explicit download
   approval, with one renderer compatibility trial before any migration.

## Implementation notes

- `tools/check_compute.py` checks the Warp spectral implementation against a Fourier reference,
  analytic mesh cases, lossless PNG, JPEG and MP4 color/frame ordering. Fixtures stay in `build/`.
- PyNvVideoCodec's packed RGB path produced full-range YUV without range metadata in this pinned
  build. `tools/video_pixels.py` computes limited-range BT.601 NV12 explicitly in Warp.
- `tools/video_io.py` drains encoder packets, uses a 90 kHz clock and disables B-frames for direct
  monotonic timestamps. Its muxer is libav-based. No ffmpeg executable is needed for MP4.
- Warp's seeded noise generator changes the noise patterns while preserving periodic spectra.
  The saved previous assets and scenes are in gitignored `build/baseline/` for local comparisons.
- README and CLAUDE.md install pins match. Public docs contain no render durations or other
  performance figures. Python text checks found no em dashes.

## Known weaknesses (presentation)

- The Ahmed body reads as a box at some angles.
- The dolly does not travel past the body.
- Slight honeycomb shimmer in motion.
- The collector is a smooth tube with little detail.

## Decisions waiting on the owner

1. SimReady materials: accept the gated dataset terms (task 10e).
2. DrivAerML body (CC-BY-SA) to replace or join the Ahmed body: a download, needs approval.
3. Phone capture of a large interior for the gsplat backdrop (task 9).
4. Licence: MIT or Apache-2.0 (README and plan say TBD).
5. Final repo name and whether it goes public.
6. Blender MCP: not installed; current direction is code-only.
