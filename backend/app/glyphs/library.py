from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.glyphs.features import gradients, orientation_histogram
from app.glyphs.contract import FONT_PATH, render_spec
from app.models.schemas import DetailLevel, Style, RenderProfile, RenderSpec


ROOT = Path(__file__).resolve().parents[2]


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
    spec: RenderSpec
    excluded_chars: tuple[str, ...] = ()


class GlyphLibrary:
    """Rasterizes glyphs once and exposes image/edge/orientation descriptors."""

    def __init__(self, config_path: Path | None = None, font_path: str | None = None):
        path = config_path or ROOT / "config" / "charsets.json"
        self.config = json.loads(path.read_text(encoding="utf-8"))
        self.font_path = font_path or str(FONT_PATH)

    @lru_cache(maxsize=24)
    def get(self, style: Style, detail: DetailLevel, profile: RenderProfile = RenderProfile.MONOSPACE) -> GlyphSet:
        chars = tuple(dict.fromkeys(self.config[style.value][detail.value]))
        return self._rasterize(chars, profile)

    def _rasterize(self, chars: tuple[str, ...], profile: RenderProfile = RenderProfile.MONOSPACE) -> GlyphSet:
        spec = render_spec(profile)
        font = ImageFont.truetype(self.font_path, spec.font_size, layout_engine=ImageFont.Layout.BASIC)
        cell_width, cell_height = spec.cell_width, spec.cell_height
        missing = bytes(font.getmask("\U0010ffff"))
        accepted, excluded = [], []
        for char in chars:
            supported = (
                char.isprintable()
                and not unicodedata.combining(char)
                and unicodedata.east_asian_width(char) not in {"W", "F"}
                and abs(font.getlength(char) - cell_width) < 0.1
                and bytes(font.getmask(char)) != missing
            )
            (accepted if supported else excluded).append(char)
        chars = tuple([" ", *(char for char in accepted if char != " ")]) if " " in accepted else tuple(accepted)
        if " " not in chars or len(chars) < 2:
            raise ValueError("Charset must include space and supported single-cell glyphs")
        patches: list[np.ndarray] = []
        for char in chars:
            canvas = Image.new("L", (cell_width, cell_height), 255)
            if char != " ":
                draw = ImageDraw.Draw(canvas)
                draw.text((0, spec.baseline), char, fill=0, font=font, anchor="ls")
            patches.append(1.0 - np.asarray(canvas, dtype=np.float32) / 255.0)
        patch_array = np.stack(patches)
        edge_array = np.stack([gradients(patch)[2] for patch in patch_array])
        densities = patch_array.mean(axis=(1, 2))
        orientations = np.stack([orientation_histogram(patch) for patch in patch_array])
        return GlyphSet(chars, patch_array, edge_array, densities, orientations, cell_width, cell_height, self.font_path, spec, tuple(excluded))
