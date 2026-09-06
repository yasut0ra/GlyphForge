from __future__ import annotations

from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 12 * 1024 * 1024


async def read_upload_image(upload: UploadFile) -> Image.Image:
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="アップロードできるのは画像ファイルです。")
    contents = await upload.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="画像は12MB以下にしてください。")
    try:
        image = Image.open(BytesIO(contents))
        image.load()
        return image
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="画像を読み取れませんでした。") from exc
