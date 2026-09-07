from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def _white_canvas_fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    canvas = Image.new("L", size, 255)
    offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
    canvas.paste(image, offset)
    return canvas


def canonical_reference(image: Image.Image) -> Image.Image:
    """The exact pixels returned to the client are reused in every refinement."""
    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    source = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
    source.thumbnail((900, 900), Image.Resampling.LANCZOS)
    return source


def prepare_target(
    image: Image.Image,
    grid_width: int,
    cell_width: int,
    cell_height: int,
    max_rows: int = 64,
) -> tuple[np.ndarray, int]:
    """Normalize contrast and fit a source to a character-aware pixel grid."""
    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    source = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("L")
    source = ImageEnhance.Contrast(source).enhance(1.45)
    source = source.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3))
    aspect = source.height / max(1, source.width)
    rows = int(round(aspect * grid_width * cell_width / cell_height))
    rows = max(8, min(max_rows, rows))
    size = (grid_width * cell_width, rows * cell_height)
    fitted = _white_canvas_fit(source, size)
    target = 1.0 - np.asarray(fitted, dtype=np.float32) / 255.0
    return target, rows
