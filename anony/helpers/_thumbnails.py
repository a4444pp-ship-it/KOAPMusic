# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import aiohttp

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)
        self.session = None

        self.blue = (0, 170, 255)
        self.cyan = (0, 225, 255)
        self.white = (245, 250, 255)
        self.muted = (155, 190, 225)

        try:
            self.font_bold = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 38
            )
            self.font_regular = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 25
            )
            self.font_small = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 19
            )
        except Exception:
            self.font_bold = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    async def start(self) -> None:
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def save_thumb(self, output_path: str, url: str) -> str:
        if not self.session:
            await self.start()

        async with self.session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.read()

        with open(output_path, "wb") as f:
            f.write(data)

        return output_path

    def rounded_cover(self, image, radius=25):
        image = image.convert("RGBA")
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (0, 0, image.width - 1, image.height - 1),
            radius=radius,
            fill=255,
        )
        image.putalpha(mask)
        return image

    def fit_text(self, draw, text, font, max_width):
        text = str(text or "Unknown")
        while text and draw.textbbox((0, 0), text, font=font)[2] > max_width:
            text = text[:-2]
        if text != str(text or ""):
            text += "..."
        return text

    def draw_glow(self, image, box, radius=30):
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.rounded_rectangle(
            box,
            radius=radius,
            outline=(0, 150, 255, 210),
            width=5,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(12))
        image.alpha_composite(glow)

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            os.makedirs("cache", exist_ok=True)

            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_koap.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            cover = Image.open(temp).convert("RGB")

            # Background
            bg = ImageOps.fit(
                cover,
                self.size,
                method=Image.Resampling.LANCZOS,
            ).filter(ImageFilter.GaussianBlur(35))

            bg = ImageEnhance.Brightness(bg).enhance(0.30)
            image = bg.convert("RGBA")

            # Dark blue overlay
            overlay = Image.new("RGBA", self.size, (2, 10, 35, 155))
            image.alpha_composite(overlay)

            draw = ImageDraw.Draw(image)

            # Header
            draw.text(
                (55, 25),
                "KOAPMUSIC",
                font=ImageFont.truetype(
                    "anony/helpers/Raleway-Bold.ttf", 58
                ),
                fill=self.white,
                stroke_width=2,
                stroke_fill=(0, 90, 220),
            )

            draw.text(
                (60, 92),
                "TELEGRAM MUSIC BOT",
                font=self.font_small,
                fill=self.cyan,
            )

            # Header equalizer
            for i in range(24):
                x = 850 + i * 14
                h = 20 + ((i * 17) % 65)
                draw.rounded_rectangle(
                    (x, 105 - h, x + 7, 105),
                    radius=3,
                    fill=(0, 170, 255, 210),
                )

            # Main panel
            draw.rounded_rectangle(
                (35, 145, 1245, 620),
                radius=35,
                fill=(2, 12, 40, 220),
                outline=(0, 135, 255, 255),
                width=3,
            )

            self.draw_glow(image, (35, 145, 1245, 620))
            draw = ImageDraw.Draw(image)

            # Album cover
            cover_size = (410, 410)
            cover = ImageOps.fit(
                cover,
                cover_size,
                method=Image.Resampling.LANCZOS,
            )
            cover = self.rounded_cover(cover, 25)

            image.alpha_composite(cover, (75, 180))

            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle(
                (75, 180, 485, 590),
                radius=25,
                outline=self.blue,
                width=4,
            )

            # Now Playing label
            draw.rounded_rectangle(
                (545, 185, 845, 245),
                radius=30,
                fill=(0, 35, 90, 230),
                outline=self.blue,
                width=2,
            )

            draw.text(
                (575, 198),
                "▮▮  NOW PLAYING",
                font=self.font_regular,
                fill=self.white,
            )

            # Song title
            title = str(song.title or "Unknown Song")
            title_font = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 43
            )

            while (
                title
                and draw.textbbox((0, 0), title, font=title_font)[2] > 660
            ):
                title = title[:-2]

            if title != str(song.title or "Unknown Song"):
                title += "..."

            draw.text(
                (545, 275),
                title,
                font=title_font,
                fill=self.white,
            )

            # Artist / channel
            artist = str(song.channel_name or "KOAPMUSIC")

            while (
                artist
                and draw.textbbox((0, 0), artist, font=self.font_regular)[2]
                > 600
            ):
                artist = artist[:-2]

            if artist != str(song.channel_name or "KOAPMUSIC"):
                artist += "..."

            draw.text(
                (550, 345),
                "♪  " + artist,
                font=self.font_regular,
                fill=self.muted,
            )

            # Progress line
            draw.rounded_rectangle(
                (550, 420, 1190, 428),
                radius=5,
                fill=(45, 75, 125, 255),
            )
            draw.rounded_rectangle(
                (550, 420, 730, 428),
                radius=5,
                fill=self.cyan,
            )

            draw.ellipse(
                (718, 410, 742, 434),
                fill=self.white,
                outline=self.blue,
                width=2,
            )

            draw.text(
                (550, 440),
                "KOAPMUSIC",
                font=self.font_small,
                fill=self.white,
            )

            duration = str(song.duration or "00:00")
            draw.text(
                (1090, 440),
                duration,
                font=self.font_small,
                fill=self.white,
            )

            # Music controls
            controls = [
                (225, "⇄", self.cyan),
                (430, "◀", self.white),
                (640, "Ⅱ", self.white),
                (850, "▶", self.white),
                (1055, "↻", self.cyan),
            ]

            for x, symbol, color in controls:
                radius = 49 if x != 640 else 65

                draw.ellipse(
                    (
                        x - radius,
                        535 - radius,
                        x + radius,
                        535 + radius,
                    ),
                    fill=(3, 20, 65, 255),
                    outline=self.blue,
                    width=3,
                )

                font = ImageFont.truetype(
                    "anony/helpers/Raleway-Bold.ttf",
                    55 if x != 640 else 70,
                )

                bbox = draw.textbbox((0, 0), symbol, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                draw.text(
                    (x - tw / 2, 535 - th / 2 - bbox[1]),
                    symbol,
                    font=font,
                    fill=color,
                )

            # Footer
            draw.rounded_rectangle(
                (40, 635, 1240, 700),
                radius=25,
                fill=(1, 12, 38, 245),
                outline=(0, 120, 255, 255),
                width=2,
            )

            draw.text(
                (90, 650),
                "Powered by KOAPMUSIC",
                font=self.font_regular,
                fill=self.white,
            )

            draw.text(
                (770, 650),
                "@KoAPmusic_bot",
                font=self.font_regular,
                fill=self.cyan,
            )

            image.convert("RGB").save(output, quality=95)

            try:
                os.remove(temp)
            except Exception:
                pass

            return output

        except Exception as e:
            print(f"Thumbnail generation error: {e}")
            return config.DEFAULT_THUMB
