from __future__ import annotations

import numpy as np


def gradients(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Central-difference gradients and magnitude for a normalized grayscale array."""
    gy, gx = np.gradient(image.astype(np.float32))
    magnitude = np.hypot(gx, gy)
    return gx, gy, magnitude


def orientation_histogram(image: np.ndarray) -> np.ndarray:
    gx, gy, magnitude = gradients(image)
    angle = np.mod(np.arctan2(gy, gx), np.pi)
    bins = np.floor(angle / (np.pi / 4)).astype(np.int32).clip(0, 3)
    hist = np.array([magnitude[bins == idx].sum() for idx in range(4)], dtype=np.float32)
    total = float(hist.sum())
    return hist / total if total > 1e-8 else hist


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    c1, c2 = 0.01**2, 0.03**2
    mean_a, mean_b = float(a.mean()), float(b.mean())
    var_a, var_b = float(a.var()), float(b.var())
    covariance = float(((a - mean_a) * (b - mean_b)).mean())
    score = ((2 * mean_a * mean_b + c1) * (2 * covariance + c2)) / (
        (mean_a**2 + mean_b**2 + c1) * (var_a + var_b + c2)
    )
    return float(np.clip(score, -1.0, 1.0))


def edge_similarity(a: np.ndarray, b: np.ndarray) -> float:
    _, _, edge_a = gradients(a)
    _, _, edge_b = gradients(b)
    return float(np.clip(1.0 - np.mean(np.abs(edge_a - edge_b)), 0.0, 1.0))
