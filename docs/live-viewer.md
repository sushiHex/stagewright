# Live USD observer

The observer displays complete saved USD revisions through NVIDIA RTX and WebRTC.
The browser displays video and controls. It does not render geometry.

Install the optional transport and its pinned browser runtime:

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-viewer.txt
.venv/Scripts/python.exe tools/setup_viewer.py
```

Check and reserve GPU capacity through vram-mcp before starting the observer or physics worker.
Publish a completed scene, then start the observer with a new session directory:

```powershell
.venv/Scripts/python.exe tools/publish.py scene.usda build/run/publications
.venv/Scripts/python.exe tools/observe.py build/run/publications --session build/run/viewer
```

Open `http://127.0.0.1:8765`. Use the revision control to inspect an earlier save.
Use the separate play control and timeline to inspect its recorded motion. Latest returns to
the newest publication and follows subsequent saves. A failed update retains the last good view.

The publisher creates an immutable USDZ containing the root and its dependencies before it
advances `current.json`. One constructor owns publication. The observer owns stage changes and
rendering. It keeps viewer cameras and render products in separate wrapper layers.

An optional `run.json` beside the publications directory, or the explicit `--run` path, supplies the exact construction prompt
and returned model fields. Requested settings and served settings remain separate; null is unknown.
Keep the complete construction evidence outside published inputs.

The runtime uses `ovstream==0.5.7` and `@nvidia/ov-web-rtc==6.8.2`. Their NVIDIA terms remain
separate from this repository's MIT license. The browser runtime stays in ignored build dependencies.
Final video exports still require converged captures; live preview frames can be progressive.

On Windows, run the observer in a logged-on user session. WebRTC needs the desktop video adapter.
The empty waiting view keeps the connection active before the first saved revision; it is not a
construction revision. Transport drops do not replace the last good scene.

`tools/engine.py` runs a candidate through the isolated physics worker and exports the actual
recorded replay. Use its `--physics-python` argument to select the pinned worker environment.
It reports measured body translation and rotation, not an automatic engineering-adequacy verdict.
The worker gets a scratch directory inside its result directory through process-local temporary
directory variables. The caller environment stays unchanged.

`tools/field_view.py` is a narrow private cached-reference adapter. It keeps source hashes and the
geometry-provenance gap explicit. The adapter alone does not verify a matched result. For the
approved reference pair, separate source-history evidence establishes the provider bundle mapping.
Keep that evidence with a new immutable publication. This is a cached reference, not fresh inference
or aerodynamic validation of a generated environment.
