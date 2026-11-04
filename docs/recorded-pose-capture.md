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

## Replay with static additions

For an additive scene, compose the existing replay above the expanded view.
Keep the original scene opinions unchanged: the replay's original-source branch
can mask weaker edits to existing geometry or materials. This reuses a recording;
it does not evaluate physics in the expanded scene.

Create the input root with the author Python, separately from rendering:

```python
from pathlib import Path
from pxr import Usd

replay = Path("build/recording/replay.usdc").resolve()
expanded = Path("build/expanded-view.usda").resolve()
recorded = Usd.Stage.Open(str(replay))
view = Usd.Stage.CreateNew("build/replay-view.usda")
view.GetRootLayer().subLayerPaths = [replay.as_posix(), expanded.as_posix()]
for key in ("defaultPrim", "upAxis", "metersPerUnit", "kilogramsPerUnit",
            "timeCodesPerSecond", "framesPerSecond", "startTimeCode", "endTimeCode"):
    value = recorded.GetMetadata(key)
    if value is not None:
        view.SetMetadata(key, value)
view.GetRootLayer().Save()
```

Stage metadata belongs on this root; sublayers do not supply its units or timing.
The expanded view must use compatible units and up axis and supply the render
product. Check representative recorded poses before capturing the full sequence.

Source sampling and encoded playback can use different rates. For example, capture
transform poses at six source samples per second, then encode them at twelve frames
per second for 2x playback.

```powershell
.venv/Scripts/python.exe tools/render_motion.py --scene build/replay-view.usda --product Review --fps 6 --count 121 --out build/replay-frames --snapshot-poses
.venv/Scripts/python.exe tools/render_motion.py --scene build/replay-view.usda --product Review --fps 12 --count 121 --out build/replay-frames --no-render --encode
```

Keep any construction reveal or playback reset labelled as presentation. A replay
reset is not a simulated return movement.
