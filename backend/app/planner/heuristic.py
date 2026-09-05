from __future__ import annotations

import re

from app.models.schemas import DetailLevel, Style, VisualPlan
from app.planner.base import LLMProvider


FEATURES: list[tuple[tuple[str, ...], str, list[str]]] = [
    (("初音ミク", "hatsune", "miku"), "Hatsune Miku", ["long twin tails", "large anime eyes", "bangs", "headset"]),
    (("猫", "cat", "kitten"), "cat", ["triangular ears", "round eyes", "whiskers", "small nose"]),
    (("宇宙船", "spaceship", "spacecraft", "rocket"), "spaceship", ["clear hull silhouette", "cockpit", "engine exhaust", "fins"]),
    (("女の子", "girl", "anime"), "anime girl", ["large expressive eyes", "hair silhouette", "small nose", "gentle expression"]),
    (("犬", "dog", "puppy"), "dog", ["ears", "bright eyes", "muzzle", "nose"]),
]


class HeuristicPlanner(LLMProvider):
    name = "local heuristic planner"

    def create_visual_plan(
        self, prompt: str, width: int, style: Style, detail: DetailLevel
    ) -> VisualPlan:
        lowered = prompt.lower().strip()
        subject = re.sub(r"(の)?(aa|ascii\s*art).*$", "", prompt, flags=re.I).strip(" 「」『』") or "requested subject"
        features = ["recognizable silhouette", "clean outer contour", "distinctive focal features"]
        canonical = subject
        for keywords, mapped_subject, mapped_features in FEATURES:
            if any(keyword in lowered for keyword in keywords):
                canonical, features = mapped_subject, mapped_features
                break

        composition = "head and shoulders" if any(k in lowered for k in ("顔", "face", "portrait", "女の子", "初音ミク")) else "single centered subject, full silhouette"
        view = "side" if any(k in lowered for k in ("横向き", "side view", "profile")) else "front"
        style_label = {
            Style.PURE_ASCII: "crisp monochrome line art optimized for printable ASCII glyphs",
            Style.UNICODE: "delicate monochrome anime line art optimized for Unicode curves",
            Style.BLOCK: "bold high-contrast silhouette optimized for block glyphs",
        }[style]
        if detail == DetailLevel.SIMPLE:
            style_label += ", minimal detail"
        elif detail == DetailLevel.DETAILED:
            style_label += ", detailed interior landmarks"

        return VisualPlan(
            subject=canonical,
            composition=composition,
            view=view,
            important_features=features,
            style=style_label,
            width=width,
        )
