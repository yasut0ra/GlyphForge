from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image, ImageDraw

from app.evaluator.screenshot_local import LocalScreenshotEvaluator
from app.feedback_service import FeedbackLoopService
from app.glyphs.library import GlyphLibrary
from app.models.schemas import DetailLevel, Style, VisualPlan
from app.service import Pipeline


def sample_line_art() -> Image.Image:
    image = Image.new("L", (180, 140), 255)
    draw = ImageDraw.Draw(image)
    draw.ellipse((25, 18, 155, 132), outline=0, width=4)
    draw.line((42, 35, 62, 4, 82, 28), fill=0, width=4)
    draw.line((98, 28, 118, 4, 138, 35), fill=0, width=4)
    draw.ellipse((65, 64, 78, 77), fill=0)
    draw.ellipse((102, 64, 115, 77), fill=0)
    return image


def decode_data_url(value: str) -> Image.Image:
    encoded = value.split(",", 1)[1]
    image = Image.open(BytesIO(base64.b64decode(encoded)))
    image.load()
    return image


def test_screenshot_evaluation_and_feedback_refinement_are_end_to_end():
    reference = sample_line_art()
    generated = Pipeline.default().generate(
        "猫の顔", 24, Style.PURE_ASCII, DetailLevel.SIMPLE, reference
    )
    evaluator = LocalScreenshotEvaluator()
    service = FeedbackLoopService(GlyphLibrary(), evaluator, evaluator)
    plan = VisualPlan(
        subject="cat face",
        composition="centered face",
        view="front",
        important_features=["ears", "eyes"],
        width=24,
    )

    evaluation = service.evaluate(plan, decode_data_url(generated.optimized_preview), reference)
    assert 0.0 <= evaluation.evaluation.overall_score <= 1.0
    assert 0.0 <= evaluation.objective_score <= 1.0
    assert evaluation.evaluation.regions
    assert evaluation.evaluator == "local screenshot evaluator"

    refined = service.refine(
        generated.optimized_aa,
        reference,
        24,
        Style.PURE_ASCII,
        DetailLevel.SIMPLE,
        1,
        evaluation.evaluation,
    )
    assert all(len(line) == 24 for line in refined.optimized_aa.splitlines())
    assert refined.reconstruction_loss <= refined.previous_reconstruction_loss + 1e-8
    assert refined.optimized_preview.startswith("data:image/png;base64,")
    assert refined.changed_characters >= 0
