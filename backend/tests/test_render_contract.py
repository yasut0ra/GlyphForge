from io import BytesIO
import json
import unicodedata

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pytest
from fastapi.testclient import TestClient

from app.glyphs.library import GlyphLibrary
from app.models.schemas import Style, DetailLevel, RenderProfile
from app.renderer.render import grid_to_image, grid_to_text
from app.renderer.preprocess import prepare_target, canonical_reference


@pytest.mark.parametrize("profile", list(RenderProfile))
def test_glyph_patches_keep_real_baseline_and_advance(profile):
    glyphs = GlyphLibrary().get(Style.PURE_ASCII, DetailLevel.DETAILED, profile)
    text = "A._|/g()"
    indices = np.array([[glyphs.chars.index(char) for char in text]])
    patches = grid_to_image(indices, glyphs)
    # Independent oracle: ordinary line text, not recentered glyph patches.
    image = Image.new("L", (len(text)*glyphs.cell_width, glyphs.cell_height), 255)
    font = ImageFont.truetype(glyphs.font_path, glyphs.spec.font_size, layout_engine=ImageFont.Layout.BASIC)
    ImageDraw.Draw(image).text((0, glyphs.spec.baseline), text, font=font, fill=0, anchor="ls")
    oracle = 1 - np.asarray(image)/255
    # Subpixel overhang at cell edges may differ; baseline shifts are much larger.
    assert np.abs(patches-oracle).mean() < 0.005
    dot = glyphs.patches[glyphs.chars.index(".")]
    uppercase = glyphs.patches[glyphs.chars.index("A")]
    assert np.argwhere(dot > 0.5)[:, 0].mean() > np.argwhere(uppercase > 0.5)[:, 0].mean() + 4
    assert grid_to_text(indices, glyphs) == text


@pytest.mark.parametrize("style", list(Style))
def test_every_advertised_glyph_has_a_single_cell_advance(style):
    glyphs = GlyphLibrary().get(style, DetailLevel.DETAILED)
    font = ImageFont.truetype(glyphs.font_path, glyphs.spec.font_size, layout_engine=ImageFont.Layout.BASIC)
    assert all(abs(font.getlength(char)-glyphs.cell_width) < 0.1 for char in glyphs.chars)
    assert all(unicodedata.east_asian_width(char) not in {"W", "F"} for char in glyphs.chars)
    assert all(not unicodedata.combining(char) for char in glyphs.chars)


def test_profile_changes_rows_before_matching_not_output_width():
    reference = Image.new("L", (100, 100), 255)
    library = GlyphLibrary()
    rows = []
    for profile in RenderProfile:
        g = library.get(Style.PURE_ASCII, DetailLevel.SIMPLE, profile)
        target, count = prepare_target(reference, 60, g.cell_width, g.cell_height)
        assert target.shape[1] == 60*g.cell_width
        rows.append(count)
    assert rows == [30, 24]


def test_transparent_and_small_images_use_white_background_and_available_grid():
    reference = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    ImageDraw.Draw(reference).rectangle((3, 2, 6, 7), fill=(0, 0, 0, 255))
    target, _ = prepare_target(reference, 40, 12, 24)
    assert target[0, 0] == 0
    assert target[:, target.shape[1]//2].max() > 0.9
    assert np.count_nonzero(target > 0.5) > target.size*0.15


def test_generate_and_refine_keep_profile_and_charset_through_api():
    from app.main import app
    image = Image.new("L", (96, 96), 255)
    ImageDraw.Draw(image).ellipse((12, 12, 84, 84), outline=0, width=4)
    data = BytesIO()
    image.save(data, format="PNG")
    files = {"image": ("circle.png", data.getvalue(), "image/png")}
    request = {"prompt": "circle", "width": "24", "style": "pure_ascii", "detail": "simple", "render_profile": "notes_docs"}
    with TestClient(app) as client:
        response = client.post("/api/generate", data=request, files=files)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["render_spec"]["cell_height"] == 30
        assert result["grid_height"] == 10
        assert all(len(line) == 24 for line in result["optimized_aa"].splitlines())
        evaluation = client.post("/api/evaluate-screenshot", data={"plan": json.dumps(result['plan'])}, files={
            "screenshot": ("aa.png", data.getvalue(), "image/png"), "reference": ("ref.png", data.getvalue(), "image/png")})
        assert evaluation.status_code == 200
        refinement = client.post("/api/refine", data={**request, "aa": result["optimized_aa"], "round_number": "1", "feedback": json.dumps(evaluation.json()['evaluation'])}, files={"reference": files['image']})
        assert refinement.status_code == 200, refinement.text
        assert refinement.json()['render_spec'] == result['render_spec']
        assert refinement.json()['reconstruction_loss'] <= result['metrics']['optimized_reconstruction_loss'] + 1e-6
        invalid = client.post("/api/generate", data={**request, "render_profile": "proportional"}, files=files)
        assert invalid.status_code == 422


def test_reference_sent_to_client_is_the_exact_refinement_target():
    from app.renderer.render import pil_to_data_url
    import base64
    image = Image.new("RGBA", (1800, 1234), (0, 0, 0, 0))
    ImageDraw.Draw(image).line((50, 50, 1750, 1200), fill="black", width=9)
    source = canonical_reference(image)
    returned = Image.open(BytesIO(base64.b64decode(pil_to_data_url(source).split(',')[1])))
    a, rows_a = prepare_target(source, 60, 12, 24)
    b, rows_b = prepare_target(returned, 60, 12, 24)
    assert rows_a == rows_b
    np.testing.assert_array_equal(a, b)
