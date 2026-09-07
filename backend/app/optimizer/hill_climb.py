from __future__ import annotations

import numpy as np

from app.glyphs.library import GlyphSet
from app.optimizer.base import OptimizationResult, Optimizer
from app.renderer.loss import legacy_reconstruction_loss as reconstruction_loss
from app.renderer.matcher import InitialMatch
from app.renderer.render import grid_to_image


class HillClimbOptimizer(Optimizer):
    """Greedy 1-glyph substitution scored in a 3x3-cell rendered neighborhood."""

    def __init__(self, max_passes: int = 2, epsilon: float = 1e-8):
        self.max_passes = max_passes
        self.epsilon = epsilon

    @staticmethod
    def _bounds(row: int, col: int, shape: tuple[int, int], glyphs: GlyphSet) -> tuple[slice, slice]:
        rows, cols = shape
        row0, row1 = max(0, row - 1), min(rows, row + 2)
        col0, col1 = max(0, col - 1), min(cols, col + 2)
        return (
            slice(row0 * glyphs.cell_height, row1 * glyphs.cell_height),
            slice(col0 * glyphs.cell_width, col1 * glyphs.cell_width),
        )

    def optimize(self, target: np.ndarray, initial: InitialMatch, glyphs: GlyphSet) -> OptimizationResult:
        indices = initial.indices.copy()
        rendered = grid_to_image(indices, glyphs)
        global_loss = reconstruction_loss(target, rendered).total
        accepted = 0
        evaluations = 0
        order = np.dstack(np.unravel_index(np.argsort(initial.cell_losses.ravel())[::-1], indices.shape))[0]

        for _ in range(self.max_passes):
            pass_changes = 0
            for row, col in order:
                y = int(row) * glyphs.cell_height
                x = int(col) * glyphs.cell_width
                local_y, local_x = self._bounds(int(row), int(col), indices.shape, glyphs)
                best_index = int(indices[row, col])
                best_loss = reconstruction_loss(target[local_y, local_x], rendered[local_y, local_x]).total
                original_patch = rendered[y : y + glyphs.cell_height, x : x + glyphs.cell_width].copy()
                for candidate in initial.candidates[row, col, 1:]:
                    candidate_index = int(candidate)
                    if candidate_index == best_index:
                        continue
                    rendered[y : y + glyphs.cell_height, x : x + glyphs.cell_width] = glyphs.patches[candidate_index]
                    trial_loss = reconstruction_loss(target[local_y, local_x], rendered[local_y, local_x]).total
                    evaluations += 1
                    if trial_loss + self.epsilon < best_loss:
                        best_loss = trial_loss
                        best_index = candidate_index
                    rendered[y : y + glyphs.cell_height, x : x + glyphs.cell_width] = original_patch

                if best_index != int(indices[row, col]):
                    rendered[y : y + glyphs.cell_height, x : x + glyphs.cell_width] = glyphs.patches[best_index]
                    trial_global_loss = reconstruction_loss(target, rendered).total
                    evaluations += 1
                    if trial_global_loss + self.epsilon < global_loss:
                        indices[row, col] = best_index
                        global_loss = trial_global_loss
                        accepted += 1
                        pass_changes += 1
                    else:
                        rendered[y : y + glyphs.cell_height, x : x + glyphs.cell_width] = original_patch
            if pass_changes == 0:
                break
        return OptimizationResult(indices=indices, iterations=accepted, evaluations=evaluations)
