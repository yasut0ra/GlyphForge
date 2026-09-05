from __future__ import annotations

import math

from PIL import Image, ImageDraw

from app.image_generation.base import ImageGenerationProvider
from app.models.schemas import VisualPlan


class ProceduralReferenceProvider(ImageGenerationProvider):
    """Offline demo provider. It yields clean line art without any API key."""

    name = "offline procedural line art"

    def generate(self, plan: VisualPlan) -> Image.Image:
        image = Image.new("L", (640, 520), 255)
        draw = ImageDraw.Draw(image)
        subject = plan.subject.lower()
        if "cat" in subject or "猫" in subject:
            self._cat(draw)
        elif any(key in subject for key in ("ship", "rocket", "宇宙船")):
            self._spaceship(draw)
        elif any(key in subject for key in ("girl", "miku", "女の子", "初音")):
            self._anime_portrait(draw, twin_tails="miku" in subject or "初音" in subject)
        else:
            self._generic_badge(draw)
        return image

    @staticmethod
    def _line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], width: int = 7) -> None:
        draw.line(points, fill=10, width=width, joint="curve")

    def _cat(self, draw: ImageDraw.ImageDraw) -> None:
        self._line(draw, [(150, 170), (185, 65), (260, 140)])
        self._line(draw, [(380, 140), (455, 65), (490, 170)])
        draw.ellipse((142, 112, 498, 460), outline=10, width=8)
        draw.arc((200, 215, 285, 300), 190, 350, fill=10, width=7)
        draw.arc((355, 215, 440, 300), 190, 350, fill=10, width=7)
        draw.polygon([(320, 300), (302, 320), (338, 320)], outline=10)
        self._line(draw, [(320, 320), (320, 340), (292, 360)], 5)
        self._line(draw, [(320, 340), (348, 360)], 5)
        for y, delta in ((322, 0), (350, 12), (378, 25)):
            self._line(draw, [(285, y), (110 - delta, y - 18)], 4)
            self._line(draw, [(355, y), (530 + delta, y - 18)], 4)

    def _spaceship(self, draw: ImageDraw.ImageDraw) -> None:
        self._line(draw, [(75, 290), (190, 235), (390, 125), (555, 260), (390, 395), (190, 325), (75, 290)], 8)
        draw.ellipse((315, 185, 440, 285), outline=10, width=7)
        self._line(draw, [(188, 238), (160, 150), (320, 185)], 7)
        self._line(draw, [(188, 324), (160, 410), (320, 370)], 7)
        self._line(draw, [(87, 270), (25, 235)], 6)
        self._line(draw, [(87, 290), (10, 290)], 6)
        self._line(draw, [(87, 310), (25, 345)], 6)
        for x in (230, 275, 320):
            draw.ellipse((x, 285, x + 24, 309), outline=10, width=4)

    def _anime_portrait(self, draw: ImageDraw.ImageDraw, twin_tails: bool) -> None:
        draw.ellipse((210, 70, 430, 385), outline=10, width=7)
        self._line(draw, [(218, 180), (250, 95), (285, 165), (320, 88), (345, 165), (390, 100), (424, 185)], 7)
        if twin_tails:
            self._line(draw, [(222, 145), (115, 175), (70, 430), (170, 360), (205, 230)], 9)
            self._line(draw, [(418, 145), (525, 175), (570, 430), (470, 360), (435, 230)], 9)
            draw.rectangle((175, 145, 222, 178), outline=10, width=6)
            draw.rectangle((418, 145, 465, 178), outline=10, width=6)
        draw.ellipse((255, 222, 300, 270), outline=10, width=6)
        draw.ellipse((340, 222, 385, 270), outline=10, width=6)
        draw.ellipse((273, 240, 286, 263), fill=10)
        draw.ellipse((358, 240, 371, 263), fill=10)
        self._line(draw, [(309, 292), (320, 298), (331, 292)], 4)
        draw.arc((285, 300, 355, 342), 15, 165, fill=10, width=5)
        self._line(draw, [(250, 390), (210, 495)], 7)
        self._line(draw, [(390, 390), (430, 495)], 7)
        self._line(draw, [(210, 495), (430, 495)], 7)

    def _generic_badge(self, draw: ImageDraw.ImageDraw) -> None:
        points = []
        for i in range(12):
            angle = -math.pi / 2 + i * math.pi / 6
            radius = 205 if i % 2 == 0 else 165
            points.append((320 + int(math.cos(angle) * radius), 265 + int(math.sin(angle) * radius)))
        draw.polygon(points, outline=10, width=8)
        draw.ellipse((215, 160, 425, 370), outline=10, width=8)
        draw.ellipse((265, 225, 292, 252), fill=10)
        draw.ellipse((348, 225, 375, 252), fill=10)
        draw.arc((270, 250, 370, 325), 10, 170, fill=10, width=7)
