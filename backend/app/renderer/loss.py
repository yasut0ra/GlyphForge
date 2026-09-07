from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.glyphs.features import gradients, orientation_histogram


@dataclass(frozen=True)
class LossBreakdown:
    total: float
    pixel: float
    edge: float
    orientation: float
    shape: float = 0.0


def legacy_reconstruction_loss(target: np.ndarray, rendered: np.ndarray) -> LossBreakdown:
    pixel = float(np.mean((target - rendered) ** 2))
    _, _, target_edge = gradients(target)
    _, _, rendered_edge = gradients(rendered)
    edge = float(np.mean((target_edge - rendered_edge) ** 2))
    target_orientation = orientation_histogram(target)
    rendered_orientation = orientation_histogram(rendered)
    orientation = float(np.mean((target_orientation - rendered_orientation) ** 2))
    total = 0.58 * pixel + 0.30 * edge + 0.12 * orientation
    return LossBreakdown(total=total, pixel=pixel, edge=edge, orientation=orientation)


def reconstruction_loss(target: np.ndarray, rendered: np.ndarray) -> LossBreakdown:
    from app.renderer.multiscale import MultiscaleObjective
    return MultiscaleObjective(target).evaluate(rendered)
