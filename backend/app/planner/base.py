from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import DetailLevel, Style, VisualPlan


class LLMProvider(ABC):
    name = "abstract"

    @abstractmethod
    def create_visual_plan(
        self, prompt: str, width: int, style: Style, detail: DetailLevel
    ) -> VisualPlan:
        """Understand the request. Implementations must not generate AA text."""
