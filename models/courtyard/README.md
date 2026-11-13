# COURTYARD / NORTH LIFT

Build the accepted workshop and its surrounding buildings from editable Python source.
One motor moves the roof and wall through simulated joints. The surrounding buildings
are static display content.

Run these commands from the repository root. Install the base environment as shown
in the main README. Use a new output directory for each build or physics run.

## Build the scene

```powershell
.venv/Scripts/python.exe models/courtyard/build.py --out build/courtyard
```

Open `build/courtyard/scene.usda` for the complete static scene. The `saves/` directory
contains eight rebuilt stages. They reproduce the accepted source stages; they are
not a new record of an agent construction session. The generator is in
`models/courtyard/source/`.

## Record the mechanism

Create the separate physics environment with the pinned requirements:

```powershell
uv venv --python .venv/Scripts/python.exe --no-python-downloads build/envs/physics
uv pip install --python build/envs/physics/Scripts/python.exe -r requirements-physics.txt
```

Check and reserve GPU capacity through vram-mcp before starting physics or RTX work.
Use one GPU worker at a time and keep the existing desktop pacing settings.

Run the original candidate and its motor-disabled control:

```powershell
.venv/Scripts/python.exe tools/engine.py build/courtyard/candidates/candidate_002.usda build/courtyard-powered --physics-python build/envs/physics/Scripts/python.exe --steps 2400 --fps 120
.venv/Scripts/python.exe tools/engine.py build/courtyard/candidates/candidate_002_motor_disabled.usda build/courtyard-control --physics-python build/envs/physics/Scripts/python.exe --steps 2400 --fps 120
```

The control changes only the drive stiffness, damping and maximum force. The engine
records body poses and exports `recording/replay.usdc` in each result directory.
It does not evaluate the physics of the added buildings.

The accepted study required at least 95% of Court C01 to be clear during the final
two seconds of its recording. The engine's body-motion summary does not measure that
opening condition. Measure it on the CPU from each result, into a new directory:

```powershell
.venv/Scripts/python.exe models/courtyard/source/measure.py build/courtyard-powered build/courtyard-powered-measure
.venv/Scripts/python.exe models/courtyard/source/measure.py build/courtyard-control build/courtyard-control-measure
```

`summary.json` states whether the measure established the condition in
`source/parameters.json`, and `clearance.csv` holds every recorded sample. The measure
projects each prim's bound, so it is a conservative lower bound on open area: a pass
establishes the condition, and a fail means only that this measure did not establish it.
The angle columns are each body's world-frame rotation about X, not a joint angle. A
recording shorter than the hold window is refused. The powered run should establish the
condition and the control should not.

## View and capture the replay

Compose the powered replay above the static display scene:

```powershell
.venv/Scripts/python.exe models/courtyard/build.py --out build/courtyard --replay build/courtyard-powered/recording/replay.usdc
```

This writes `build/courtyard/motion.usda`. It does not rebuild the source or run
physics. The root keeps the replay metadata and the fixed Comparison camera.

Start with three recorded poses:

```powershell
.venv/Scripts/python.exe tools/render_motion.py --scene build/courtyard/motion.usda --product Review --fps 6 --count 121 --frames 0,60,120 --res 1920x1080 --spp 32 --supersample 1 --snapshot-poses --out build/courtyard-probe
```

The PNG files show the start, middle and end of the recording from one fixed view.
The snapshot path samples recorded poses. It adds no simulated motion.

For a full clip, repeat the capture without `--frames` and set `--out` to
`build/courtyard-frames`. After the full capture finishes, encode those frames:

```powershell
.venv/Scripts/python.exe tools/render_motion.py --scene build/courtyard/motion.usda --product Review --fps 12 --count 121 --out build/courtyard-frames --no-render --encode
```

The output is `build/courtyard-frames/review.mp4`. Capture and encoding run in
separate processes. The clip contains one recorded opening, not a simulated closing
cycle. No original solver recording or construction record is included in this package.

COURTYARD is a conceptual presentation environment. Its pose records do not establish
structural adequacy, contact safety, actuator sizing or aerodynamic behavior.

Packaging checks cover source parity, composition and selected RTX captures. The default
USD validator still reports inherited mesh normals, topology and grouping issues.
This package preserves those parts of the accepted source. Generated meshes carry an
extent computed from their points; no point, face or transform differs from the accepted source.
