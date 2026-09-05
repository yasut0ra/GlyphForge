from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.glyphs.features import gradients, orientation_histogram
from app.glyphs.library import GlyphSet


@dataclass
class InitialMatch:
    indices: np.ndarray
    candidates: np.ndarray
    cell_losses: np.ndarray


def _cell_feature_loss(cell: np.ndarray, glyphs: GlyphSet) -> np.ndarray:
    pixel_loss = np.mean((glyphs.patches - cell[None, :, :]) ** 2, axis=(1, 2))
    _, _, cell_edge = gradients(cell)
    edge_loss = np.mean((glyphs.edge_patches - cell_edge[None, :, :]) ** 2, axis=(1, 2))
    orientation = orientation_histogram(cell)
    orientation_loss = np.mean((glyphs.orientations - orientation[None, :]) ** 2, axis=1)
    density_loss = (glyphs.densities - float(cell.mean())) ** 2
    return 0.54 * pixel_loss + 0.23 * edge_loss + 0.18 * orientation_loss + 0.05 * density_loss


def match_glyphs(target: np.ndarray, glyphs: GlyphSet, candidate_count: int = 7) -> InitialMatch:
    rows = target.shape[0] // glyphs.cell_height
    cols = target.shape[1] // glyphs.cell_width
    indices = np.zeros((rows, cols), dtype=np.int16)
    candidates = np.zeros((rows, cols, min(candidate_count, len(glyphs.chars))), dtype=np.int16)
    losses = np.zeros((rows, cols), dtype=np.float32)
    for row in range(rows):
        y = row * glyphs.cell_height
        for col in range(cols):
            x = col * glyphs.cell_width
            cell = target[y : y + glyphs.cell_height, x : x + glyphs.cell_width]
            cell_loss = _cell_feature_loss(cell, glyphs)
            ordered = np.argsort(cell_loss)[: candidates.shape[2]]
            candidates[row, col] = ordered
            indices[row, col] = ordered[0]
            losses[row, col] = cell_loss[ordered[0]]
    return InitialMatch(indices=indices, candidates=candidates, cell_losses=losses)
