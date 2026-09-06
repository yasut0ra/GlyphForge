from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from PIL import Image

from app.models.schemas import ScreenshotAssessment, VisualPlan


class SemanticEvaluator(ABC):
    name = "abstract"

    @abstractmethod
    def evaluate(self, plan: VisualPlan, rendered: np.ndarray, target: np.ndarray) -> float:
        """Return a semantic similarity score in [0, 1]."""


class ScreenshotEvaluator(ABC):
    """Evaluate the exact browser rasterization without rewriting the AA itself."""

    name = "abstract screenshot evaluator"

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    def evaluate(
        self, plan: VisualPlan, screenshot: Image.Image, reference: Image.Image
    ) -> ScreenshotAssessment:
        """Return structured, region-aware feedback for the rendered AA."""
