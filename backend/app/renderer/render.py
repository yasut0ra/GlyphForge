from __future__ import annotations

from io import BytesIO
import base64

import numpy as np
from PIL import Image

from app.glyphs.library import GlyphSet


def grid_to_image(indices: np.ndarray, glyphs: GlyphSet) -> np.ndarray:
    rows, cols = indices.shape
    rendered = np.zeros((rows * glyphs.cell_height, cols * glyphs.cell_width), dtype=np.float32)
    for row in range(rows):
        y = row * glyphs.cell_height
        for col in range(cols):
            x = col * glyphs.cell_width
            rendered[y : y + glyphs.cell_height, x : x + glyphs.cell_width] = glyphs.patches[indices[row, col]]
    return rendered


def grid_to_text(indices: np.ndarray, glyphs: GlyphSet) -> str:
    return "\n".join("".join(glyphs.chars[index] for index in row) for row in indices)


def ink_array_to_data_url(image: np.ndarray, scale: int = 2) -> str:
    pixels = np.clip((1.0 - image) * 255.0, 0, 255).astype(np.uint8)
    pil = Image.fromarray(pixels, mode="L")
    if scale != 1:
        pil = pil.resize((pil.width * scale, pil.height * scale), Image.Resampling.NEAREST)
    output = BytesIO()
    pil.save(output, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def pil_to_data_url(image: Image.Image, max_size: int = 900) -> str:
    normalized = image.convert("RGB")
    normalized.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    output = BytesIO()
    normalized.save(output, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")
