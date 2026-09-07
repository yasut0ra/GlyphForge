from PIL import Image, ImageDraw
import pytest

from app.models.schemas import DetailLevel, Style, RenderProfile
from app.service import Pipeline


def sample_line_art() -> Image.Image:
    image = Image.new("L", (180, 140), 255)
    draw = ImageDraw.Draw(image)
    draw.ellipse((25, 18, 155, 132), outline=0, width=4)
    draw.line((42, 35, 62, 4, 82, 28), fill=0, width=4)
    draw.line((98, 28, 118, 4, 138, 35), fill=0, width=4)
    draw.ellipse((65, 64, 78, 77), fill=0)
    draw.ellipse((102, 64, 115, 77), fill=0)
    draw.line((90, 80, 90, 92), fill=0, width=3)
    return image


def test_pipeline_preserves_width_and_never_worsens_loss():
    result = Pipeline.default().generate(
        "猫の顔", 40, Style.PURE_ASCII, DetailLevel.SIMPLE, sample_line_art()
    )
    assert all(len(line) == 40 for line in result.optimized_aa.splitlines())
    assert result.metrics.optimized_reconstruction_loss <= result.metrics.initial_reconstruction_loss + 1e-8
    assert result.metrics.number_of_characters == 40 * result.grid_height
    assert result.reference_image.startswith("data:image/png;base64,")


def test_all_styles_use_distinct_configurable_charsets():
    pipeline = Pipeline.default()
    image = sample_line_art()
    allowed = pipeline.glyphs.config
    for style in Style:
        result = pipeline.generate("test subject", 24, style, DetailLevel.SIMPLE, image)
        used = set(result.optimized_aa.replace("\n", ""))
        assert used.issubset(set(allowed[style.value]["simple"]))


@pytest.mark.parametrize("width,style,detail,profile", [
    (60, Style.UNICODE, DetailLevel.DETAILED, RenderProfile.NOTES_DOCS),
    (80, Style.BLOCK, DetailLevel.NORMAL, RenderProfile.MONOSPACE),
])
def test_wider_grids_preserve_profile_and_improve_loss(width, style, detail, profile):
    pipeline = Pipeline.default()
    result = pipeline.generate("猫の顔", width, style, detail, sample_line_art(), profile)
    assert all(len(line) == width for line in result.optimized_aa.splitlines())
    assert result.render_spec.profile == profile
    assert result.metrics.optimized_reconstruction_loss <= result.metrics.initial_reconstruction_loss
    assert set(result.optimized_aa.replace("\n", "")) <= set(pipeline.glyphs.get(style, detail, profile).chars)
