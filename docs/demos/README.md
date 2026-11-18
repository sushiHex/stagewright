# Recorded demonstrations

Three static players retain the original movies and synchronized HTML/SVG indicators.
The gallery uses no renderer, live physics worker or external JavaScript dependency.
The gallery embeds one player and starts its recorded motion with the overlays visible.
Selecting another demo replaces that player. Standalone pages start on a still; press
Play to show the saved stages and motion. Hiding the page pauses playback.

- **Four-bar linkage:** an early zero-gravity readiness rig. The forward motion comes
  from recorded PhysX poses. The return uses reverse playback. Rounded links and
  mounts are display geometry over that recording.
- **COURTYARD:** eight actual saved construction stages, then the original powered
  recording in the expanded scene. The later site additions are static. The graph
  compares powered and motor-disabled runs; the cyan arrow is pose-derived velocity.
- **Inspection hall:** two authored saves, a separate recorded deployed state and
  forward motion. The graph compares powered and motor-disabled runs. Repeat resets
  the display; it does not show a simulated closing operation.

The PNGs are the original saved images. The MP4 files retain their original bytes.
Pose samples and video-to-sample mappings are unchanged. Local machine paths and
internal execution instructions are omitted. Configured model settings remain
separate from the unknown served model and effective effort.

Build the current models from [COURTYARD](https://github.com/sushiHex/stagewright/blob/main/models/courtyard/README.md) and
[inspection hall](https://github.com/sushiHex/stagewright/blob/main/models/inspection_hall/README.md). These historical captures
are presentation records, not a claim that every frame comes from the latest source.

## Hosting

GitHub Pages can serve these files directly: select `main` and `/docs` under
**Settings > Pages > Build and deployment > Deploy from a branch**. No custom workflow
or build command is needed. `docs/.nojekyll` keeps the site static.

The gallery address is `https://sushihex.github.io/stagewright/demos/` once Pages is
enabled. The pages also open locally. Directory links use explicit `index.html` paths.
