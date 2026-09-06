from __future__ import annotations

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from app.evaluator.base import ScreenshotEvaluator
from app.glyphs.features import edge_similarity, ssim
from app.models.schemas import EvaluationRegion, ScreenshotAssessment, VisualPlan


def _ink_canvas(image: Image.Image, size: tuple[int, int] = (384, 384)) -> np.ndarray:
    source = ImageOps.exif_transpose(image).convert("L")
    source = ImageEnhance.Contrast(source).enhance(1.35)
    source.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("L", size, 255)
    offset = ((size[0] - source.width) // 2, (size[1] - source.height) // 2)
    canvas.paste(source, offset)
    return 1.0 - np.asarray(canvas, dtype=np.float32) / 255.0


class LocalScreenshotEvaluator(ScreenshotEvaluator):
    """API-free fallback that scores browser raster structure and weak regions."""

    name = "local screenshot evaluator"

    def evaluate(
        self, plan: VisualPlan, screenshot: Image.Image, reference: Image.Image
    ) -> ScreenshotAssessment:
        rendered = _ink_canvas(screenshot)
        target = _ink_canvas(reference)
        structural = float(np.clip(ssim(target, rendered), 0.0, 1.0))
        edges = edge_similarity(target, rendered)
        coverage = float(rendered.mean())
        readability = float(np.clip(1.0 - abs(coverage - 0.16) / 0.28, 0.0, 1.0))
        silhouette = float(np.clip(0.62 * edges + 0.38 * structural, 0.0, 1.0))
        feature = float(np.clip(0.48 * structural + 0.32 * edges + 0.20 * readability, 0.0, 1.0))
        subject = float(np.clip(0.58 * silhouette + 0.42 * feature, 0.0, 1.0))
        overall = float(
            np.clip(
                0.30 * subject + 0.26 * silhouette + 0.24 * feature + 0.20 * readability,
                0.0,
                1.0,
            )
        )

        error = np.abs(target - rendered)
        cells: list[tuple[float, int, int]] = []
        for row in range(3):
            for col in range(3):
                y0, y1 = row * 128, (row + 1) * 128
                x0, x1 = col * 128, (col + 1) * 128
                cells.append((float(error[y0:y1, x0:x1].mean()), row, col))
        worst = sorted(cells, reverse=True)[:2]
        peak = max((item[0] for item in worst), default=1.0) or 1.0
        regions = [
            EvaluationRegion(
                x=round(col / 3, 4),
                y=round(row / 3, 4),
                width=round(1 / 3, 4),
                height=round(1 / 3, 4),
                issue_type="browser_rendering",
                description="参照輪郭との差が大きい領域です。文字形状を再探索します。",
                priority=round(min(1.0, value / peak), 4),
            )
            for value, row, col in worst
        ]
        return ScreenshotAssessment(
            subject_score=round(subject, 4),
            silhouette_score=round(silhouette, 4),
            feature_score=round(feature, 4),
            readability_score=round(readability, 4),
            overall_score=round(overall, 4),
            summary=f"{plan.subject}のブラウザ描画を参照画像との構造差で評価しました。",
            suggested_adjustment="差が大きい領域を優先し、glyph候補数と局所探索範囲を増やします。",
            regions=regions,
        )
