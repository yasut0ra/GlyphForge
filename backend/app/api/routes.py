from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.uploads import read_upload_image
from app.feedback_service import FeedbackLoopService
from app.models.schemas import (
    DetailLevel,
    GenerationResponse,
    RefinementResponse,
    ScreenshotAssessment,
    ScreenshotEvaluationResponse,
    Style,
    VisualPlan,
    RenderProfile,
)
from app.planner.heuristic import HeuristicPlanner
from app.planner.openai_provider import OpenAIPlanner
from app.service import Pipeline


router = APIRouter(prefix="/api")
pipeline = Pipeline.default()
feedback_loop = FeedbackLoopService.default()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/plan", response_model=VisualPlan)
def plan(prompt: str = Form(...), width: int = Form(60), style: Style = Form(Style.PURE_ASCII), detail: DetailLevel = Form(DetailLevel.NORMAL)) -> VisualPlan:
    online = OpenAIPlanner()
    if online.available:
        try:
            return online.create_visual_plan(prompt, width, style, detail)
        except Exception:
            pass
    return HeuristicPlanner().create_visual_plan(prompt, width, style, detail)


@router.post("/generate", response_model=GenerationResponse)
async def generate(
    prompt: str = Form(..., min_length=1, max_length=500),
    width: int = Form(60, ge=20, le=120),
    style: Style = Form(Style.PURE_ASCII),
    detail: DetailLevel = Form(DetailLevel.NORMAL),
    image: UploadFile | None = File(None),
    render_profile: RenderProfile = Form(RenderProfile.MONOSPACE),
) -> GenerationResponse:
    uploaded = await read_upload_image(image) if image is not None else None
    try:
        return await run_in_threadpool(pipeline.generate, prompt, width, style, detail, uploaded, render_profile)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AA生成に失敗しました: {exc}") from exc


@router.post("/evaluate-screenshot", response_model=ScreenshotEvaluationResponse)
async def evaluate_screenshot(
    plan: str = Form(...),
    screenshot: UploadFile = File(...),
    reference: UploadFile = File(...),
) -> ScreenshotEvaluationResponse:
    try:
        visual_plan = VisualPlan.model_validate_json(plan)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Visual Planを読み取れませんでした。") from exc
    screenshot_image = await read_upload_image(screenshot)
    reference_image = await read_upload_image(reference)
    return await run_in_threadpool(feedback_loop.evaluate, visual_plan, screenshot_image, reference_image)


@router.post("/refine", response_model=RefinementResponse)
async def refine(
    aa: str = Form(...),
    width: int = Form(..., ge=20, le=120),
    style: Style = Form(...),
    detail: DetailLevel = Form(...),
    round_number: int = Form(..., ge=1, le=3),
    feedback: str = Form(...),
    reference: UploadFile = File(...),
    render_profile: RenderProfile = Form(RenderProfile.MONOSPACE),
) -> RefinementResponse:
    try:
        assessment = ScreenshotAssessment.model_validate_json(feedback)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Screenshot評価を読み取れませんでした。") from exc
    reference_image = await read_upload_image(reference)
    try:
        return await run_in_threadpool(feedback_loop.refine, aa, reference_image, width, style, detail, round_number, assessment, render_profile)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AA改善に失敗しました: {exc}") from exc
