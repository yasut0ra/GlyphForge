from __future__ import annotations

import base64
from io import BytesIO
import json
import os
import urllib.request

from PIL import Image

from app.evaluator.base import ScreenshotEvaluator
from app.models.schemas import ScreenshotAssessment, VisualPlan


def _image_data_url(image: Image.Image, max_size: int = 768) -> str:
    normalized = image.convert("RGB")
    normalized.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    output = BytesIO()
    normalized.save(output, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _output_text(payload: dict) -> str:
    text = ""
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text += content.get("text", "")
    return text


class OpenAIScreenshotEvaluator(ScreenshotEvaluator):
    """Optional multimodal evaluator for semantic, silhouette, and feature fidelity."""

    name = "OpenAI screenshot evaluator"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv(
            "OPENAI_EVALUATOR_MODEL", os.getenv("OPENAI_PLANNER_MODEL", "gpt-5.4-mini")
        )

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def evaluate(
        self, plan: VisualPlan, screenshot: Image.Image, reference: Image.Image
    ) -> ScreenshotAssessment:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        schema = ScreenshotAssessment.model_json_schema()
        body = {
            "model": self.model,
            "store": False,
            "instructions": (
                "Evaluate browser-rendered ASCII art against the requested subject and reference line art. "
                "Return only structured assessment data. Never rewrite or directly generate ASCII art. "
                "Judge recognizability, silhouette, preservation of important features, and browser readability. "
                "Regions use normalized x/y/width/height coordinates and must contain at most three high-impact issues."
            ),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Subject: {plan.subject}\nComposition: {plan.composition}\n"
                                f"View: {plan.view}\nImportant features: {', '.join(plan.important_features)}\n"
                                "First image: exact browser rendering of the AA. Second image: reference line art."
                            ),
                        },
                        {"type": "input_image", "image_url": _image_data_url(screenshot), "detail": "low"},
                        {"type": "input_image", "image_url": _image_data_url(reference), "detail": "low"},
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "screenshot_assessment",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read())
        text = _output_text(payload)
        if not text:
            raise RuntimeError("The screenshot evaluator returned no structured output")
        return ScreenshotAssessment.model_validate_json(text)
