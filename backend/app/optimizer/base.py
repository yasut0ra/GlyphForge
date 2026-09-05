from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from app.glyphs.library import GlyphSet
from app.renderer.matcher import InitialMatch


@dataclass
class OptimizationResult:
    indices: np.ndarray
    iterations: int
    evaluations: int


class Optimizer(ABC):
    @abstractmethod
    def optimize(self, target: np.ndarray, initial: InitialMatch, glyphs: GlyphSet) -> OptimizationResult:
        """Optimize a discrete glyph grid against a rendered target."""
