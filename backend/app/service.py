from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from PIL import Image

from app.evaluator.dummy import StructuralSemanticEvaluator
from app.glyphs.features import edge_similarity, ssim
from app.glyphs.library import GlyphLibrary
from app.image_generation.base import ImageGenerationProvider
from app.image_generation.openai_provider import OpenAIImageGenerationProvider
from app.image_generation.procedural import ProceduralReferenceProvider
from app.models.schemas import DetailLevel, GenerationMetrics, GenerationResponse, Style, RenderProfile
from app.optimizer.coordinate import CoordinateOptimizer
from app.planner.base import LLMProvider
from app.planner.heuristic import HeuristicPlanner
from app.planner.openai_provider import OpenAIPlanner
from app.renderer.loss import reconstruction_loss
from app.renderer.matcher import match_glyphs
from app.renderer.preprocess import prepare_target, canonical_reference
from app.renderer.render import grid_to_image, grid_to_text, ink_array_to_data_url, pil_to_data_url


@dataclass
class Pipeline:
    glyphs: GlyphLibrary
    offline_planner: LLMProvider
    image_provider: ImageGenerationProvider
    evaluator: StructuralSemanticEvaluator

    @classmethod
    def default(cls) -> "Pipeline":
        online_image = OpenAIImageGenerationProvider()
        image_provider: ImageGenerationProvider = online_image if online_image.available else ProceduralReferenceProvider()
        return cls(GlyphLibrary(), HeuristicPlanner(), image_provider, StructuralSemanticEvaluator())

    def _planner(self) -> LLMProvider:
        online = OpenAIPlanner()
        return online if online.available else self.offline_planner

    def generate(
        self,
        prompt: str,
        width: int,
        style: Style,
        detail: DetailLevel,
        uploaded_image: Image.Image | None = None,
        render_profile: RenderProfile = RenderProfile.MONOSPACE,
    ) -> GenerationResponse:
        started = perf_counter()
        planner = self._planner()
        try:
            plan = planner.create_visual_plan(prompt, width, style, detail)
        except Exception:
            planner = self.offline_planner
            plan = planner.create_visual_plan(prompt, width, style, detail)

        active_image_provider = self.image_provider
        if uploaded_image is not None:
            reference = uploaded_image.copy()
        else:
            try:
                reference = active_image_provider.generate(plan)
            except Exception:
                active_image_provider = ProceduralReferenceProvider()
                reference = active_image_provider.generate(plan)
        reference = canonical_reference(reference)
        glyph_set = self.glyphs.get(style, detail, render_profile)
        target, rows = prepare_target(reference, width, glyph_set.cell_width, glyph_set.cell_height)
        initial = match_glyphs(target, glyph_set)
        initial_render = grid_to_image(initial.indices, glyph_set)
        initial_loss = reconstruction_loss(target, initial_render)

        pass_count = {DetailLevel.SIMPLE: 1, DetailLevel.NORMAL: 2, DetailLevel.DETAILED: 3}[detail]
        optimized = CoordinateOptimizer(max_passes=pass_count, pair_budget=36 if detail == DetailLevel.DETAILED else 0).optimize(target, initial, glyph_set)
        optimized_render = grid_to_image(optimized.indices, glyph_set)
        optimized_loss = reconstruction_loss(target, optimized_render)
        # Numerical safeguard, independent of the optimizer implementation.
        if optimized_loss.total > initial_loss.total:
            optimized.indices = initial.indices.copy()
            optimized.iterations = 0
            optimized.joint_replacements = 0
            optimized_render = initial_render.copy()
            optimized_loss = initial_loss
        semantic = self.evaluator.evaluate(plan, optimized_render, target)

        metrics = GenerationMetrics(
            initial_reconstruction_loss=round(initial_loss.total, 6),
            optimized_reconstruction_loss=round(optimized_loss.total, 6),
            optimization_iterations=optimized.iterations,
            optimization_evaluations=optimized.evaluations,
            generation_time_ms=round((perf_counter() - started) * 1000),
            number_of_characters=width * rows,
            ssim=round(max(0.0, ssim(target, optimized_render)), 4),
            edge_similarity=round(edge_similarity(target, optimized_render), 4),
            semantic_score=round(semantic, 4),
            structure_score=round(semantic, 4),
            optimization_passes=optimized.passes,
            joint_replacements=optimized.joint_replacements,
        )
        return GenerationResponse(
            plan=plan,
            initial_aa=grid_to_text(initial.indices, glyph_set),
            optimized_aa=grid_to_text(optimized.indices, glyph_set),
            reference_image=pil_to_data_url(reference),
            initial_preview=ink_array_to_data_url(initial_render),
            optimized_preview=ink_array_to_data_url(optimized_render),
            metrics=metrics,
            grid_width=width,
            grid_height=rows,
            render_spec=glyph_set.spec,
            style=style,
            detail=detail,
            warnings=["選択フォントで1セルに収まらない文字を除外: " + "".join(glyph_set.excluded_chars)] if glyph_set.excluded_chars else [],
            providers={
                "planner": planner.name,
                "image": "uploaded image" if uploaded_image is not None else active_image_provider.name,
                "semantic": self.evaluator.name,
            },
        )
