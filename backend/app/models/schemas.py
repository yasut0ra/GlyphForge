from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Style(str, Enum):
    PURE_ASCII = "pure_ascii"
    UNICODE = "unicode"
    BLOCK = "block"


class DetailLevel(str, Enum):
    SIMPLE = "simple"
    NORMAL = "normal"
    DETAILED = "detailed"


class VisualPlan(BaseModel):
    subject: str
    composition: str = "centered subject"
    view: str = "front"
    important_features: list[str] = Field(default_factory=list)
    style: str = "monochrome high-contrast line art"
    width: int = Field(default=60, ge=20, le=120)


class GenerationMetrics(BaseModel):
    initial_reconstruction_loss: float
    optimized_reconstruction_loss: float
    optimization_iterations: int
    optimization_evaluations: int
    generation_time_ms: int
    number_of_characters: int
    ssim: float
    edge_similarity: float
    semantic_score: float


class GenerationResponse(BaseModel):
    plan: VisualPlan
    initial_aa: str
    optimized_aa: str
    reference_image: str
    initial_preview: str
    optimized_preview: str
    metrics: GenerationMetrics
    grid_width: int
    grid_height: int
    providers: dict[str, str]
