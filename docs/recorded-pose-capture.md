# Recorded transform capture

Use `tools/render_motion.py --snapshot-poses` when a recorded rigid-body sequence
does not advance correctly through retained-stage time updates. This explicit path
samples the source USD transforms in a separate author process, then renders each
static pose through a fresh native stage. Sample counts, output size and codecs
use the normal render options.

```powershell
.venv/Scripts/python.exe tools/render_motion.py --scene build/replay-view.usda --product Review --fps 12 --count 121 --out build/replay-frames --snapshot-poses
```

The scene must supply `/Render/Review`. Frame indices select source seconds as
`frame / fps`; the source stage's time-code rate controls USD sampling. Use
`--frames` for a bounded selection before a full sequence.

This path supports transform animation, including camera transforms. Other
animated properties and animated transforms inside instance proxies are rejected.
Static instances remain composed. Transform order, reset stacks, stage units and
the original scene remain intact. Temporary sample layers are removed at exit.

The default retained-stage camera path is unchanged. This option does not simulate
physics or add motion; it samples existing authored or recorded transforms.
