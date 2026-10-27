"""Repository paths and the default procedural model."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "wind_tunnel"
ASSETS = MODEL / "assets"
SCENES = MODEL / "scenes"
DOCS = MODEL / "docs"
MEDIA = MODEL / "media"
