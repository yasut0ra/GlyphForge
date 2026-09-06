from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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


class EvaluationRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)
    issue_type: str
    description: str
    priority: float = Field(ge=0.0, le=1.0)


class ScreenshotAssessment(BaseModel):
    """Structured feedback produced from the browser-rendered AA image."""

    model_config = ConfigDict(extra="forbid")

    subject_score: float = Field(ge=0.0, le=1.0)
    silhouette_score: float = Field(ge=0.0, le=1.0)
    feature_score: float = Field(ge=0.0, le=1.0)
    readability_score: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    summary: str
    suggested_adjustment: str
    regions: list[EvaluationRegion] = Field(max_length=3)


class ScreenshotEvaluationResponse(BaseModel):
    evaluation: ScreenshotAssessment
    objective_score: float = Field(ge=0.0, le=1.0)
    evaluator: str


class RefinementResponse(BaseModel):
    optimized_aa: str
    optimized_preview: str
    previous_reconstruction_loss: float
    reconstruction_loss: float
    ssim: float
    edge_similarity: float
    optimization_iterations: int
    optimization_evaluations: int
    changed_characters: int
    grid_width: int
    grid_height: int
