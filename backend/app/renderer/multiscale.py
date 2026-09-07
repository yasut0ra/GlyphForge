"""Spatial, foreground-normalized objective with an exact finite-support delta.

Every term is a sum of pixel contributions. A glyph replacement changes only
its support + a four-pixel halo; unlike a global orientation histogram, the
same objective can therefore be used for local search and global reporting.
Initialization uses these feature types but cell-local normalization.
"""
from __future__ import annotations

import numpy as np

from app.glyphs.features import gradients
from app.renderer.loss import LossBreakdown


def box_blur(image: np.ndarray, radius: int) -> np.ndarray:
    if radius == 0:
        return image
    size = radius * 2 + 1
    padded = np.pad(image.astype(np.float64), radius, mode="edge")
    integral = np.pad(padded, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    return ((integral[size:, size:] - integral[:-size, size:]
             - integral[size:, :-size] + integral[:-size, :-size]) / size**2).astype(np.float32)


def features(image: np.ndarray) -> tuple[np.ndarray, ...]:
    gx, gy, edge = gradients(image)
    safe = np.maximum(edge, 1e-6)
    # Unsigned structure tensor retains orientation AT each pixel. Opposing
    # edges on the two sides of a stroke share the same orientation.
    orientation = np.stack((gx * gx / safe, gy * gy / safe, np.sqrt(2) * gx * gy / safe))
    return image, edge, orientation, box_blur(image, 1), box_blur(image, 4)


class MultiscaleObjective:
    radius = 4
    version = "multiscale-v2"
    weights = (0.25, 0.15, 0.10, 0.20, 0.30)

    def __init__(self, target: np.ndarray):
        self.target = features(target)
        self.pixel_weights = 1.0 + 4.0 * self.target[-1]
        self.normalizers = [
            max(float(np.sum(item * item * (self.pixel_weights if i == 0 else 1))), target.size * 0.0005)
            for i, item in enumerate(self.target)
        ]
        # Flat tonal regions have almost no target gradient. Dividing edge
        # error by that tiny energy makes every textured glyph worse than
        # blank. Bound both derivative terms by the available ink energy.
        ink_energy = float(np.sum(target * target, dtype=np.float64))
        for i in (1, 2):
            self.normalizers[i] = max(self.normalizers[i], 0.20 * ink_energy)
        # Tone art necessarily introduces glyph texture that isn't present in
        # a flat gray reference. Route low-gradient inputs toward shape/tone
        # matching; keep full derivative weights for actual line art.
        edge_energy = float(np.sum(self.target[1] ** 2, dtype=np.float64))
        structure = min(1.0, (edge_energy / max(0.03 * ink_energy, 1e-8)) ** 0.5)
        self.weights = (0.25, 0.15 * structure, 0.10 * structure, 0.20, 0.55 - 0.25 * structure)

    def _terms(self, actual: tuple[np.ndarray, ...], region: tuple[slice, slice]) -> list[float]:
        terms = []
        for i, item in enumerate(actual):
            reference = self.target[i][(..., *region)]
            delta = (item - reference) ** 2
            if i == 0:
                delta = delta * self.pixel_weights[region]
            terms.append(float(np.sum(delta, dtype=np.float64)) / self.normalizers[i])
        return terms

    def evaluate(self, rendered: np.ndarray) -> LossBreakdown:
        terms = self._terms(features(rendered), (slice(None), slice(None)))
        return LossBreakdown(
            total=float(np.dot(self.weights, terms)), pixel=terms[0], edge=terms[1],
            orientation=terms[2], shape=(terms[3] + terms[4]) / 2,
        )

    def region_score(self, rendered: np.ndarray, bounds: tuple[int, int, int, int]) -> float:
        """Contribution affected by a change inside y0:y1, x0:x1.

        Two halos are needed: one for changed contributions and one to compute
        the filters of those contributions without artificial crop boundaries.
        Normalization is always global and target-only.
        """
        y0, y1, x0, x1 = bounds
        height, width = rendered.shape
        r = self.radius
        a, b, c, d = max(0, y0-r), min(height, y1+r), max(0, x0-r), min(width, x1+r)
        ay, by, cx, dx = max(0, a-r), min(height, b+r), max(0, c-r), min(width, d+r)
        cropped = features(rendered[ay:by, cx:dx])
        interior = (slice(a-ay, b-ay), slice(c-cx, d-cx))
        actual = tuple(item[(..., *interior)] for item in cropped)
        terms = self._terms(actual, (slice(a, b), slice(c, d)))
        return float(np.dot(self.weights, terms))
