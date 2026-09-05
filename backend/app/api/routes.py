from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.models.schemas import DetailLevel, GenerationResponse, Style, VisualPlan
from app.planner.heuristic import HeuristicPlanner
from app.planner.openai_provider import OpenAIPlanner
from app.service import Pipeline


router = APIRouter(prefix="/api")
pipeline = Pipeline.default()


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
) -> GenerationResponse:
    uploaded = None
    if image is not None:
        if image.content_type and not image.content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="アップロードできるのは画像ファイルです。")
        contents = await image.read()
        if len(contents) > 12 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="画像は12MB以下にしてください。")
        try:
            uploaded = Image.open(BytesIO(contents))
            uploaded.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail="画像を読み取れませんでした。") from exc
    try:
        return pipeline.generate(prompt, width, style, detail, uploaded)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AA生成に失敗しました: {exc}") from exc
