from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from app.evaluator.base import ScreenshotEvaluator
from app.evaluator.openai_screenshot import OpenAIScreenshotEvaluator
from app.evaluator.screenshot_local import LocalScreenshotEvaluator
from app.glyphs.features import edge_similarity, ssim
from app.glyphs.library import GlyphLibrary
from app.models.schemas import (
    DetailLevel,
    RefinementResponse,
    ScreenshotAssessment,
    ScreenshotEvaluationResponse,
    Style,
    VisualPlan,
)
from app.optimizer.hill_climb import HillClimbOptimizer
from app.renderer.loss import reconstruction_loss
from app.renderer.matcher import InitialMatch, match_glyphs
from app.renderer.preprocess import prepare_target
from app.renderer.render import grid_to_image, grid_to_text, ink_array_to_data_url, text_to_grid


@dataclass
class FeedbackLoopService:
    glyphs: GlyphLibrary
    online_evaluator: ScreenshotEvaluator
    offline_evaluator: ScreenshotEvaluator

    @classmethod
    def default(cls) -> "FeedbackLoopService":
        return cls(GlyphLibrary(), OpenAIScreenshotEvaluator(), LocalScreenshotEvaluator())

    def evaluate(
        self, plan: VisualPlan, screenshot: Image.Image, reference: Image.Image
    ) -> ScreenshotEvaluationResponse:
        local_assessment = self.offline_evaluator.evaluate(plan, screenshot, reference)
        evaluator = self.online_evaluator if self.online_evaluator.available else self.offline_evaluator
        try:
            assessment = (
                local_assessment
                if evaluator is self.offline_evaluator
                else evaluator.evaluate(plan, screenshot, reference)
            )
        except Exception:
            evaluator = self.offline_evaluator
            assessment = local_assessment
        return ScreenshotEvaluationResponse(
            evaluation=assessment,
            objective_score=local_assessment.overall_score,
            evaluator=evaluator.name,
        )

    def refine(
        self,
        aa_text: str,
        reference: Image.Image,
        width: int,
        style: Style,
        detail: DetailLevel,
        round_number: int,
        feedback: ScreenshotAssessment,
    ) -> RefinementResponse:
        glyph_set = self.glyphs.get(style, detail)
        target, rows = prepare_target(reference, width, glyph_set.cell_width, glyph_set.cell_height)
        current_indices = text_to_grid(aa_text, glyph_set, width, rows)
        current_render = grid_to_image(current_indices, glyph_set)
        current_loss = reconstruction_loss(target, current_render)

        candidate_count = min(len(glyph_set.chars), 7 + max(1, round_number) * 6)
        matched = match_glyphs(target, glyph_set, candidate_count=candidate_count)
        candidates = np.empty_like(matched.candidates)
        for row in range(rows):
            for col in range(width):
                current = int(current_indices[row, col])
                alternatives = [int(value) for value in matched.candidates[row, col] if int(value) != current]
                ordered = [current, *alternatives]
                while len(ordered) < candidate_count:
                    ordered.append(current)
                candidates[row, col] = ordered[:candidate_count]

        cell_height, cell_width = glyph_set.cell_height, glyph_set.cell_width
        cell_errors = np.zeros((rows, width), dtype=np.float32)
        for row in range(rows):
            y0, y1 = row * cell_height, (row + 1) * cell_height
            for col in range(width):
                x0, x1 = col * cell_width, (col + 1) * cell_width
                cell_errors[row, col] = float(
                    np.mean(np.abs(target[y0:y1, x0:x1] - current_render[y0:y1, x0:x1]))
                )

        # Feedback changes search priority, while final acceptance still uses the full reconstruction loss.
        priorities = cell_errors.copy()
        for region in feedback.regions:
            row0 = max(0, min(rows - 1, int(region.y * rows)))
            row1 = max(row0 + 1, min(rows, int(np.ceil((region.y + region.height) * rows))))
            col0 = max(0, min(width - 1, int(region.x * width)))
            col1 = max(col0 + 1, min(width, int(np.ceil((region.x + region.width) * width))))
            priorities[row0:row1, col0:col1] *= 1.0 + 3.0 * region.priority

        seed = InitialMatch(indices=current_indices, candidates=candidates, cell_losses=priorities)
        optimized = HillClimbOptimizer(max_passes=min(5, round_number + 2)).optimize(
            target, seed, glyph_set
        )
        rendered = grid_to_image(optimized.indices, glyph_set)
        loss = reconstruction_loss(target, rendered)
        changed = int(np.count_nonzero(optimized.indices != current_indices))
        return RefinementResponse(
            optimized_aa=grid_to_text(optimized.indices, glyph_set),
            optimized_preview=ink_array_to_data_url(rendered),
            previous_reconstruction_loss=round(current_loss.total, 6),
            reconstruction_loss=round(loss.total, 6),
            ssim=round(max(0.0, ssim(target, rendered)), 4),
            edge_similarity=round(edge_similarity(target, rendered), 4),
            optimization_iterations=optimized.iterations,
            optimization_evaluations=optimized.evaluations,
            changed_characters=changed,
            grid_width=width,
            grid_height=rows,
        )
