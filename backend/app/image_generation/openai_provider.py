from __future__ import annotations

import base64
from io import BytesIO
import json
import os
import urllib.request

from PIL import Image

from app.image_generation.base import ImageGenerationProvider
from app.models.schemas import VisualPlan


class OpenAIImageGenerationProvider(ImageGenerationProvider):
    """Optional OpenAI Images API provider; configured entirely through env vars."""

    name = "OpenAI image generation"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, plan: VisualPlan) -> Image.Image:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        prompt = (
            f"Subject: {plan.subject}. Composition: {plan.composition}. View: {plan.view}. "
            f"Important visible features: {', '.join(plan.important_features)}. "
            "Create isolated monochrome black ink line art on a pure white background, centered, "
            "high contrast, bold clean silhouette, sparse interior lines, no text, no shading, "
            "designed specifically for conversion into a coarse ASCII character grid."
        )
        body = {
            "model": self.model,
            "prompt": prompt,
            "size": "1024x1024",
            "quality": "low",
            "n": 1,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read())
        encoded = payload["data"][0]["b64_json"]
        image = Image.open(BytesIO(base64.b64decode(encoded)))
        image.load()
        return image
