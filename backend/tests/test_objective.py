import numpy as np
import pytest

from app.glyphs.features import edge_similarity, ssim
from app.glyphs.library import GlyphLibrary
from app.models.schemas import Style, DetailLevel
from app.optimizer.coordinate import CoordinateOptimizer
from app.renderer.matcher import match_glyphs
from app.renderer.multiscale import MultiscaleObjective
from app.renderer.render import grid_to_image


@pytest.mark.parametrize("bounds", [(0, 8, 0, 12), (15, 40, 23, 47), (30, 48, 30, 60), (0, 48, 0, 60)])
def test_local_delta_matches_complete_rerender_including_boundaries(bounds):
    rng = np.random.default_rng(47)
    target, original = rng.random((2, 48, 60), dtype=np.float32)
    trial = original.copy()
    a, b, c, d = bounds
    trial[a:b, c:d] = rng.random((b-a, d-c), dtype=np.float32)
    objective = MultiscaleObjective(target)
    delta = objective.region_score(trial, bounds) - objective.region_score(original, bounds)
    full_delta = objective.evaluate(trial).total - objective.evaluate(original).total
    assert delta == pytest.approx(full_delta, abs=2e-7)


def test_blank_output_does_not_score_as_a_correct_contour():
    target = np.zeros((64, 64), dtype=np.float32)
    target[12:52, 30:33] = 1
    blank = np.zeros_like(target)
    objective = MultiscaleObjective(target)
    assert objective.evaluate(target).total == 0
    assert objective.evaluate(blank).total > 0.8
    assert edge_similarity(target, blank) == 0
    assert edge_similarity(target, target) == 1
    assert ssim(target, target) == pytest.approx(1)


def test_optimization_preserves_measured_global_objective_every_pass():
    glyphs = GlyphLibrary().get(Style.PURE_ASCII, DetailLevel.SIMPLE)
    rng = np.random.default_rng(123)
    truth = rng.integers(0, len(glyphs.chars), size=(3, 6))
    target = grid_to_image(truth, glyphs)
    target = 0.7*target + 0.3*np.roll(target, 2, axis=1)
    initial = match_glyphs(target, glyphs)
    result = CoordinateOptimizer(max_passes=3, pair_budget=20).optimize(target, initial, glyphs)
    assert all(b <= a+1e-7 for a, b in zip(result.loss_history, result.loss_history[1:]))
    assert result.loss_history[-1] <= result.loss_history[0]
    assert result.evaluations > 0
    assert result.indices.shape == initial.indices.shape


@pytest.mark.parametrize("level", [0.35, 0.65, 1.0])
def test_tonal_blocks_do_not_collapse_to_blank(level):
    glyphs = GlyphLibrary().get(Style.BLOCK, DetailLevel.NORMAL)
    target = np.full((glyphs.cell_height*3, glyphs.cell_width*6), level, dtype=np.float32)
    initial = match_glyphs(target, glyphs)
    result = CoordinateOptimizer(max_passes=2).optimize(target, initial, glyphs)
    rendered = grid_to_image(result.indices, glyphs)
    objective = MultiscaleObjective(target)
    assert rendered.mean() > level * 0.4
    assert objective.evaluate(rendered).total < objective.evaluate(np.zeros_like(target)).total
