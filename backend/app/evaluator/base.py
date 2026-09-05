from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from app.models.schemas import VisualPlan


class SemanticEvaluator(ABC):
    name = "abstract"

    @abstractmethod
    def evaluate(self, plan: VisualPlan, rendered: np.ndarray, target: np.ndarray) -> float:
        """Return a semantic similarity score in [0, 1]."""
