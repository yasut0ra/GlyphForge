"""Generate the checked-in UI example with the real offline pipeline."""
import base64
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["OPENAI_API_KEY"] = ""
from app.models.schemas import Style, DetailLevel
from app.service import Pipeline

root = Path(__file__).resolve().parents[2]
result = Pipeline.default().generate("猫の顔", 40, Style.PURE_ASCII, DetailLevel.NORMAL).model_dump(mode="json")
for field, filename in [("reference_image", "sample-reference.png"), ("initial_preview", "sample-aa-initial.png"), ("optimized_preview", "sample-aa-optimized.png")]:
    (root / "frontend/public" / filename).write_bytes(base64.b64decode(result[field].split(",")[1]))
    result[field] = "/" + filename
(root / "frontend/lib/sample-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
print(json.dumps(result["metrics"], indent=2))
