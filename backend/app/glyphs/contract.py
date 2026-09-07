"""Single source of geometry for Pillow, browser text, Canvas and clipboard."""
from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import RenderProfile, RenderSpec

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((PROJECT_ROOT / "frontend/lib/render-contract.json").read_text())
FONT_PATH = PROJECT_ROOT / "frontend/public/fonts" / CONTRACT["font_file"]


def render_spec(profile: RenderProfile = RenderProfile.MONOSPACE) -> RenderSpec:
    geometry = CONTRACT["profiles"][profile.value]
    return RenderSpec(
        profile=profile,
        font_family=CONTRACT["font_family"],
        font_size=CONTRACT["font_size"],
        font_advance=CONTRACT["font_advance"],
        cell_width=CONTRACT["cell_width"],
        cell_height=geometry["cell_height"],
        baseline=geometry["baseline"],
        version=CONTRACT["version"],
    )
