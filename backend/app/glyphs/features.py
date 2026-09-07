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
    from app.renderer.multiscale import box_blur
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    c1, c2 = 0.01**2, 0.03**2
    mean_a, mean_b = box_blur(a, 5), box_blur(b, 5)
    var_a = np.maximum(0, box_blur(a*a, 5) - mean_a**2)
    var_b = np.maximum(0, box_blur(b*b, 5) - mean_b**2)
    covariance = box_blur(a*b, 5) - mean_a*mean_b
    score = ((2 * mean_a * mean_b + c1) * (2 * covariance + c2)) / (
        (mean_a**2 + mean_b**2 + c1) * (var_a + var_b + c2)
    )
    return float(np.clip(score.mean(), -1.0, 1.0))


def edge_similarity(a: np.ndarray, b: np.ndarray) -> float:
    _, _, edge_a = gradients(a)
    _, _, edge_b = gradients(b)
    # Tolerant edge F1 counts foreground edges only. An all-white result must
    # not receive ~99% merely because most of the canvas is background.
    aa, bb = edge_a > 0.08, edge_b > 0.08
    if not aa.any() or not bb.any():
        return float(not aa.any() and not bb.any())
    def dilate(mask: np.ndarray) -> np.ndarray:
        p = np.pad(mask, 1)
        return np.logical_or.reduce([p[y:y+mask.shape[0], x:x+mask.shape[1]] for y in range(3) for x in range(3)])
    precision = float((bb & dilate(aa)).sum() / bb.sum())
    recall = float((aa & dilate(bb)).sum() / aa.sum())
    return 2 * precision * recall / max(precision + recall, 1e-8)
