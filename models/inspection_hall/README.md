# Inspection hall

A procedural, two-level vehicle inspection hall built from COURTYARD. One motor
opens the roof and deploys an elevated deck through passive revolute joints.
The source uses OpenUSD Exchange SDK and the shared COURTYARD geometry helpers.

Use the installed authoring environment for these commands. Build into a new directory:

```sh
.venv/Scripts/python.exe -I -B models/inspection_hall/build.py --out build/inspection-hall
```

Run each candidate separately with the installed physics environment. Reserve GPU
capacity first and use the project desktop controls for local runs.

```sh
.venv/Scripts/python.exe -B tools/engine.py build/inspection-hall/candidates/powered.usda build/inspection-powered --physics-python build/envs/physics/Scripts/python.exe --steps 2400 --fps 120
.venv/Scripts/python.exe -B tools/engine.py build/inspection-hall/candidates/motor_disabled.usda build/inspection-control --physics-python build/envs/physics/Scripts/python.exe --steps 2400 --fps 120
.venv/Scripts/python.exe -I -B models/inspection_hall/source/measure.py build/inspection-powered build/inspection-powered-measures --design models/inspection_hall/source/design.json
.venv/Scripts/python.exe -I -B models/inspection_hall/source/measure.py build/inspection-control build/inspection-control-measures --design models/inspection_hall/source/design.json --control
```

The control changes only drive stiffness, damping and maximum force to zero.
The CPU measurement tool reads the frozen USD and recorded poses. It checks the
last two seconds for portal and overhead opening, deck height and levelness,
headroom, gallery access and stable hold. It checks hinge separation throughout
the recording. Regions and thresholds are in `source/design.json`; the measurement
code defines the conservative bounding-box calculations. The authored closed
state must start with both openings at most 5% clear. The disabled-drive prediction
is a closed hall with roof and deck rotations within 2 degrees.

Saved stages show the authored closed hall. `recording/replay.usdc` contains the
solver motion; the build does not author body animation. Display vehicles,
stairs and galleries are static. This conceptual environment is an unloaded
rigid-body experiment. It does not establish structural strength, contact safety,
actuator loads, human access safety or loss-of-power behavior when deployed.

Native OpenUSD validation reports no findings. The NVIDIA default preset reports
missing grouping types, mesh normals and ASCII-array findings, including findings
in new content. This model does not pass that preset. The solver and measured
operation checks are separate from those authoring findings.
