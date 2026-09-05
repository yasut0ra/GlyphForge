from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from app.models.schemas import VisualPlan


class ImageGenerationProvider(ABC):
    name = "abstract"

    @abstractmethod
    def generate(self, plan: VisualPlan) -> Image.Image:
        """Generate a high-contrast reference suitable for glyph conversion."""
