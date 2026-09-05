from __future__ import annotations

import json
import os
import urllib.request

from app.models.schemas import DetailLevel, Style, VisualPlan
from app.planner.base import LLMProvider


class OpenAIPlanner(LLMProvider):
    """Optional planner using the OpenAI Responses API through the standard library."""

    name = "OpenAI visual planner"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_PLANNER_MODEL", "gpt-5.4-mini")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def create_visual_plan(
        self, prompt: str, width: int, style: Style, detail: DetailLevel
    ) -> VisualPlan:
        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        schema = VisualPlan.model_json_schema()
        schema["additionalProperties"] = False
        schema["required"] = list(schema["properties"])
        body = {
            "model": self.model,
            "instructions": (
                "Convert the request into a visual plan for an image-to-glyph renderer. "
                "Never output ASCII art. Favor a centered, high-contrast, simple-background composition."
            ),
            "input": f"Request: {prompt}\nWidth: {width}\nGlyph style: {style.value}\nDetail: {detail.value}",
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "visual_plan",
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
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())
        output_text = ""
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    output_text += content.get("text", "")
        if not output_text:
            raise RuntimeError("The planner returned no structured text output")
        plan = VisualPlan.model_validate_json(output_text)
        plan.width = width
        return plan
