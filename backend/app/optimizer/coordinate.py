from __future__ import annotations

from itertools import product

import numpy as np

from app.glyphs.library import GlyphSet
from app.optimizer.base import OptimizationResult, Optimizer
from app.renderer.matcher import InitialMatch
from app.renderer.multiscale import MultiscaleObjective
from app.renderer.render import grid_to_image


class CoordinateOptimizer(Optimizer):
    """Exact objective deltas, followed by a bounded joint two-cell search.

    Adjacent substitutions can cross a local minimum where neither single
    replacement improves the objective. No VLM scores enter move acceptance.
    """

    def __init__(self, max_passes: int = 2, pair_budget: int = 24, epsilon: float = 1e-9):
        self.max_passes, self.pair_budget, self.epsilon = max_passes, pair_budget, epsilon

    def optimize(self, target: np.ndarray, initial: InitialMatch, glyphs: GlyphSet) -> OptimizationResult:
        indices = initial.indices.copy()
        rendered = grid_to_image(indices, glyphs)
        objective = MultiscaleObjective(target)
        history = [objective.evaluate(rendered).total]
        accepted = evaluations = joint = passes = 0
        h, w = glyphs.cell_height, glyphs.cell_width
        # Stable ordering is intentional: no hidden random state in benchmarks.
        order = [tuple(map(int, rc)) for rc in np.argwhere(np.ones(indices.shape, dtype=bool))]
        order.sort(key=lambda rc: -float(initial.cell_losses[rc]))

        def search(cells: list[tuple[int, int]], choices: list[list[int]]) -> bool:
            nonlocal evaluations, accepted, joint
            bounds = (min(r for r, _ in cells)*h, (max(r for r, _ in cells)+1)*h,
                      min(c for _, c in cells)*w, (max(c for _, c in cells)+1)*w)
            original = tuple(int(indices[rc]) for rc in cells)
            best, best_loss = original, objective.region_score(rendered, bounds)

            def write(values: tuple[int, ...]) -> None:
                for (r, c), index in zip(cells, values):
                    rendered[r*h:(r+1)*h, c*w:(c+1)*w] = glyphs.patches[index]

            for trial in product(*choices):
                if trial == original:
                    continue
                write(trial)
                loss = objective.region_score(rendered, bounds)
                evaluations += 1
                if loss + self.epsilon < best_loss:
                    best, best_loss = trial, loss
            write(best)
            if best == original:
                return False
            for rc, value in zip(cells, best):
                indices[rc] = value
            accepted += 1
            joint += int(sum(a != b for a, b in zip(best, original)) > 1)
            return True

        for _ in range(self.max_passes):
            before = accepted
            for r, c in order:
                # An empty target AND current patch has no boundary to improve.
                if target[r*h:(r+1)*h, c*w:(c+1)*w].max() == 0 and indices[r, c] == 0:
                    continue
                choices = list(dict.fromkeys([int(indices[r, c]), *map(int, initial.candidates[r, c])]))
                search([(r, c)], [choices])

            # Search the highest remaining reconstruction errors, not fixed
            # initial errors, so the pair budget follows the current weak spots.
            residual = ((target-rendered)**2).reshape(indices.shape[0], h, indices.shape[1], w).mean((1, 3))
            ranked = sorted(order, key=lambda rc: -float(residual[rc]))
            pairs = 0
            for r, c in ranked:
                if pairs >= self.pair_budget or residual[r, c] < 1e-8:
                    break
                for rr, cc in ((r, c+1), (r+1, c)):
                    if rr >= indices.shape[0] or cc >= indices.shape[1] or pairs >= self.pair_budget:
                        continue
                    cells = [(r, c), (rr, cc)]
                    choices = [list(dict.fromkeys([int(indices[rc]), *map(int, initial.candidates[rc][:3])])) for rc in cells]
                    search(cells, choices)
                    pairs += 1
            passes += 1
            history.append(objective.evaluate(rendered).total)
            if accepted == before:
                break
        return OptimizationResult(indices, accepted, evaluations, passes, joint, tuple(history))
