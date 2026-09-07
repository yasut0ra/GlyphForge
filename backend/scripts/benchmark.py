"""Offline controlled ablation: same font, target, width and charset.

Compares v1 matcher/loss/search with v2 matcher/loss/coordinate search. This is NOT a
semantic benchmark or a comparison of different reference-image generators.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.glyphs.features import edge_similarity, ssim
from app.glyphs.library import GlyphLibrary
from app.image_generation.procedural import ProceduralReferenceProvider
from app.models.schemas import Style, DetailLevel, VisualPlan, RenderProfile
from app.optimizer.hill_climb import HillClimbOptimizer
from app.optimizer.coordinate import CoordinateOptimizer
from app.renderer.matcher import match_glyphs
from app.renderer.multiscale import MultiscaleObjective, box_blur
from app.renderer.preprocess import prepare_target
from app.renderer.render import grid_to_image, grid_to_text


def fixtures():
    provider = ProceduralReferenceProvider()
    for subject in ("cat", "spaceship", "anime girl"):
        yield subject.replace(" ", "-"), provider.generate(VisualPlan(subject=subject))
    # Additional tests do not come from the reference provider: asymmetric
    # contours, thin strokes and tonal blocks expose different failure modes.
    lines = Image.new("L", (320, 240), 255)
    draw = ImageDraw.Draw(lines)
    draw.line([(18, 220), (80, 22), (180, 150), (295, 34)], fill=0, width=3)
    draw.arc((30, 60, 200, 225), 35, 300, fill=0, width=3)
    yield "thin-asymmetric", lines
    tones = np.tile(np.linspace(255, 0, 320, dtype=np.uint8), (240, 1))
    yield "tone-ramp", Image.fromarray(tones)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("work/benchmark-v2"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, reference in fixtures():
        styles = [Style.BLOCK] if name == "tone-ramp" else [Style.PURE_ASCII]
        # Both line-height contracts, plus one Unicode fixture, keep the run bounded.
        if name == "cat":
            styles.append(Style.UNICODE)
        for style in styles:
            for profile in RenderProfile:
                g = GlyphLibrary().get(style, DetailLevel.NORMAL, profile)
                target, _ = prepare_target(reference, 40, g.cell_width, g.cell_height)
                objective = MultiscaleObjective(target)
                entries = {}
                images = [target]
                for version in ("v1", "v2"):
                    start = perf_counter()
                    initial = match_glyphs(target, g, legacy=version == "v1")
                    optimizer = HillClimbOptimizer(max_passes=2) if version == "v1" else CoordinateOptimizer(max_passes=2, pair_budget=0)
                    optimized = optimizer.optimize(target, initial, g)
                    elapsed = perf_counter()-start
                    rendered = grid_to_image(optimized.indices, g)
                    # Blurred F1 is independent of v2's squared-loss weights.
                    ta, ra = box_blur(target, 4), box_blur(rendered, 4)
                    shape_f1 = 2*float(np.minimum(ta, ra).sum()) / max(float(ta.sum()+ra.sum()), 1e-8)
                    entries[version] = {"loss_v2": objective.evaluate(rendered).total,
                                        "shape_f1": shape_f1, "edge_f1": edge_similarity(target, rendered),
                                        "ssim": ssim(target, rendered), "seconds": elapsed,
                                        "moves": optimized.iterations, "joint_moves": optimized.joint_replacements,
                                        "initial_loss_v2": objective.evaluate(grid_to_image(initial.indices, g)).total}
                    (args.output / f"{name}-{style.value}-{profile.value}-{version}.txt").write_text(grid_to_text(optimized.indices, g))
                    images.append(rendered)
                result = {"subject": name, "style": style.value, "profile": profile.value, **entries}
                results.append(result)
                print(json.dumps(result), flush=True)
                panel = Image.new("RGB", (3*target.shape[1], target.shape[0]+32), "white")
                draw = ImageDraw.Draw(panel)
                for i, (label, ink) in enumerate(zip(("Target", "v1 loss/search", "v2 loss/search"), images)):
                    draw.text((i*target.shape[1]+4, 4), f"{name} {style.value} {profile.value} | {label}", fill="black")
                    panel.paste(Image.fromarray(np.clip((1-ink)*255, 0, 255).astype(np.uint8)), (i*target.shape[1], 32))
                panel.save(args.output / f"{name}-{style.value}-{profile.value}.png")
    report = {"comparison": "same baseline-v2 font/profile/charset; v1 vs v2 matcher/objective/search",
              "width": 40, "cases": results,
              "mean": {version: {metric: float(np.mean([case[version][metric] for case in results]))
                                  for metric in ("loss_v2", "shape_f1", "edge_f1", "ssim", "seconds")}
                       for version in ("v1", "v2")}}
    (args.output / "results.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report['mean'], indent=2), flush=True)


if __name__ == "__main__":
    main()
