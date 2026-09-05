from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.glyphs.features import gradients, orientation_histogram
from app.models.schemas import DetailLevel, Style


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FONT_CANDIDATES = (
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)


@dataclass(frozen=True)
class GlyphSet:
    chars: tuple[str, ...]
    patches: np.ndarray
    edge_patches: np.ndarray
    densities: np.ndarray
    orientations: np.ndarray
    cell_width: int
    cell_height: int
    font_path: str


class GlyphLibrary:
    """Rasterizes glyphs once and exposes image/edge/orientation descriptors."""

    def __init__(self, config_path: Path | None = None, font_path: str | None = None):
        path = config_path or ROOT / "config" / "charsets.json"
        self.config = json.loads(path.read_text(encoding="utf-8"))
        self.font_path = font_path or next((p for p in DEFAULT_FONT_CANDIDATES if Path(p).exists()), DEFAULT_FONT_CANDIDATES[-1])

    @lru_cache(maxsize=12)
    def get(self, style: Style, detail: DetailLevel) -> GlyphSet:
        chars = tuple(dict.fromkeys(self.config[style.value][detail.value]))
        return self._rasterize(chars)

    def _rasterize(self, chars: tuple[str, ...]) -> GlyphSet:
        font_size = 18
        font = ImageFont.truetype(self.font_path, font_size)
        cell_width, cell_height = 12, 22
        patches: list[np.ndarray] = []
        for char in chars:
            canvas = Image.new("L", (cell_width, cell_height), 255)
            if char != " ":
                draw = ImageDraw.Draw(canvas)
                bbox = draw.textbbox((0, 0), char, font=font)
                glyph_w, glyph_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (cell_width - glyph_w) / 2 - bbox[0]
                y = (cell_height - glyph_h) / 2 - bbox[1]
                draw.text((x, y), char, fill=0, font=font)
            patches.append(1.0 - np.asarray(canvas, dtype=np.float32) / 255.0)
        patch_array = np.stack(patches)
        edge_array = np.stack([gradients(patch)[2] for patch in patch_array])
        densities = patch_array.mean(axis=(1, 2))
        orientations = np.stack([orientation_histogram(patch) for patch in patch_array])
        return GlyphSet(chars, patch_array, edge_array, densities, orientations, cell_width, cell_height, self.font_path)
