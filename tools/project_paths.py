"""Repository paths and the default procedural model."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "wind_tunnel"
ASSETS = MODEL / "assets"
SCENES = MODEL / "scenes"
DOCS = MODEL / "docs"
MEDIA = MODEL / "media"

# Output cadence belongs to each authored motion, shared by builder and renderer.
MOTION_SETTINGS = {
    "Dolly": {"fps": 24, "frames": 216, "loop": False},
    "Orbit360": {"fps": 24, "frames": 360, "loop": True},
}
