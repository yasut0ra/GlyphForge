from __future__ import annotations

import numpy as np

from app.evaluator.base import SemanticEvaluator
from app.glyphs.features import edge_similarity, ssim
from app.models.schemas import VisualPlan


class StructuralSemanticEvaluator(SemanticEvaluator):
    """API-free placeholder using structure; replace with a VLM/vision encoder later."""

    name = "structural proxy evaluator"

    def evaluate(self, plan: VisualPlan, rendered: np.ndarray, target: np.ndarray) -> float:
        structural = max(0.0, ssim(target, rendered))
        edges = edge_similarity(target, rendered)
        return float(np.clip(0.55 * structural + 0.45 * edges, 0.0, 1.0))
