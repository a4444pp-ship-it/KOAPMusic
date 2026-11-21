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

        # Dark blue & cyan glassmorphism palette
        self.blue = (0, 150, 255)
        self.cyan = (0, 225, 255)
        self.bright_cyan = (110, 240, 255)
        self.white = (248, 252, 255)
        self.soft_white = (225, 238, 248)
        self.muted = (165, 198, 225)

        self.glass_fill = (8, 28, 66, 158)
        self.glass_border = (120, 225, 255, 175)
        self.badge_fill = (20, 58, 105, 170)
        self.footer_fill = (6, 22, 54, 175)

        try:
            self.font_logo = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 56
            )
            self.font_title = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 40
            )
            self.font_subtitle = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 27
            )
            self.font_badge = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 20
            )
            self.font_regular = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 24
            )
            self.font_small = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 19
            )
        except Exception:
            self.font_logo = ImageFont.load_default()
            self.font_title = ImageFont.load_default()
            self.font_subtitle = ImageFont.load_default()
            self.font_badge = ImageFont.load_default()
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

    def rounded_cover(self, image: Image.Image, radius: int = 28) -> Image.Image:
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

    def fit_text(
        self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int
    ) -> str:
        clean = " ".join(str(text or "Unknown").split())
        if draw.textbbox((0, 0), clean, font=font)[2] <= max_width:
            return clean

        ellipsis = "..."
        trimmed = clean
        while trimmed:
            trimmed = trimmed[:-1].rstrip()
            candidate = trimmed + ellipsis
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                return candidate

        return ellipsis

    def draw_glow_box(
        self,
        image: Image.Image,
        box: tuple[int, int, int, int],
        radius: int = 36,
        glow_color: tuple[int, int, int, int] = (0, 210, 255, 115),
        blur_radius: int = 18,
    ) -> None:
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.rounded_rectangle(
            box,
            radius=radius,
            outline=glow_color,
            width=7,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(blur_radius))
        image.alpha_composite(glow)

    def draw_ambient_rays(self, image: Image.Image) -> None:
        rays = Image.new("RGBA", image.size, (0, 0, 0, 0))
        rd = ImageDraw.Draw(rays)

        # Top cyan accent glow and horizontal light streaks
        rd.ellipse((140, 80, 1140, 210), fill=(0, 210, 255, 38))
        rd.ellipse((180, 545, 1100, 645), fill=(0, 180, 255, 34))
        rd.rounded_rectangle((220, 126, 1060, 132), radius=3, fill=(120, 235, 255, 85))
        rd.rounded_rectangle((260, 588, 1020, 593), radius=3, fill=(120, 235, 255, 75))

        rays = rays.filter(ImageFilter.GaussianBlur(14))
        image.alpha_composite(rays)

    def draw_header_and_eq(self, image: Image.Image) -> None:
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        # Top-left KOAPMUSIC logo & subtitle
        draw.text(
            (55, 22),
            "KOAPMUSIC",
            font=self.font_logo,
            fill=self.white,
            stroke_width=2,
            stroke_fill=(0, 95, 210),
        )
        draw.text(
            (58, 86),
            "TELEGRAM MUSIC BOT",
            font=self.font_small,
            fill=self.cyan,
        )

        # Top-right cyan equalizer bars
        heights = [
            28, 44, 62, 38, 78, 52, 92, 46, 70, 34, 86, 56,
            40, 76, 48, 88, 60, 36, 68, 44, 54, 30, 42, 22,
        ]
        start_x = 875
        base_y = 104
        for idx, h in enumerate(heights):
            x = start_x + idx * 14
            bar_color = self.bright_cyan if h >= 70 else self.cyan
            draw.rounded_rectangle(
                (x, base_y - h, x + 7, base_y),
                radius=3,
                fill=(bar_color[0], bar_color[1], bar_color[2], 225),
            )

        image.alpha_composite(layer)

    def draw_transport_controls(
        self, draw: ImageDraw.ImageDraw, center_x: int, center_y: int
    ) -> None:
        # Center glass Play/Pause button
        r = 48
        draw.ellipse(
            (center_x - r, center_y - r, center_x + r, center_y + r),
            fill=(30, 85, 145, 155),
            outline=(140, 235, 255, 185),
            width=3,
        )

        # Pause bars
        bar_w = 9
        bar_h = 30
        gap = 8
        left_x = center_x - gap - bar_w
        right_x = center_x + gap
        top_y = center_y - bar_h // 2

        draw.rounded_rectangle(
            (left_x, top_y, left_x + bar_w, top_y + bar_h),
            radius=4,
            fill=self.white,
        )
        draw.rounded_rectangle(
            (right_x, top_y, right_x + bar_w, top_y + bar_h),
            radius=4,
            fill=self.white,
        )

        # Previous (<<)
        prev_x = center_x - 132
        draw.polygon(
            [
                (prev_x, center_y - 16),
                (prev_x, center_y + 16),
                (prev_x - 21, center_y),
            ],
            fill=self.soft_white,
        )
        draw.polygon(
            [
                (prev_x + 19, center_y - 16),
                (prev_x + 19, center_y + 16),
                (prev_x - 2, center_y),
            ],
            fill=self.soft_white,
        )

        # Next (>>)
        next_x = center_x + 132
        draw.polygon(
            [
                (next_x, center_y - 16),
                (next_x, center_y + 16),
                (next_x + 21, center_y),
            ],
            fill=self.soft_white,
        )
        draw.polygon(
            [
                (next_x - 19, center_y - 16),
                (next_x - 19, center_y + 16),
                (next_x + 2, center_y),
            ],
            fill=self.soft_white,
        )

    def draw_volume_bar(
        self, draw: ImageDraw.ImageDraw, center_x: int, y: int
    ) -> None:
        # Speaker icon
        spk_x = center_x - 148
        draw.polygon(
            [
                (spk_x - 9, y - 5),
                (spk_x - 2, y - 5),
                (spk_x + 7, y - 13),
                (spk_x + 7, y + 13),
                (spk_x - 2, y + 5),
                (spk_x - 9, y + 5),
            ],
            fill=self.soft_white,
        )

        # Volume slider track
        bar_left = center_x - 122
        bar_right = center_x + 122
        bar_h = 7
        draw.rounded_rectangle(
            (bar_left, y - bar_h // 2, bar_right, y + bar_h // 2),
            radius=4,
            fill=(160, 200, 235, 105),
        )

        fill_x = bar_left + int((bar_right - bar_left) * 0.62)
        draw.rounded_rectangle(
            (bar_left, y - bar_h // 2, fill_x, y + bar_h // 2),
            radius=4,
            fill=self.cyan,
        )

        knob_r = 9
        draw.ellipse(
            (fill_x - knob_r, y - knob_r, fill_x + knob_r, y + knob_r),
            fill=self.white,
            outline=self.cyan,
            width=2,
        )

        # Sound wave arcs
        wave_x = center_x + 142
        draw.arc(
            (wave_x - 7, y - 7, wave_x + 5, y + 7),
            start=-55,
            end=55,
            fill=self.bright_cyan,
            width=2,
        )
        draw.arc(
            (wave_x - 11, y - 12, wave_x + 11, y + 12),
            start=-55,
            end=55,
            fill=self.bright_cyan,
            width=2,
        )

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            os.makedirs("cache", exist_ok=True)

            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_koap.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            raw_cover = Image.open(temp).convert("RGB")

            # 1. Deep dark-blue blurred background
            bg = ImageOps.fit(
                raw_cover,
                self.size,
                method=Image.Resampling.LANCZOS,
            ).filter(ImageFilter.GaussianBlur(48))
            bg = ImageEnhance.Brightness(bg).enhance(0.32)
            bg = ImageEnhance.Color(bg).enhance(1.25)
            image = bg.convert("RGBA")

            dark_overlay = Image.new("RGBA", self.size, (3, 14, 38, 165))
            image.alpha_composite(dark_overlay)

            # 2. Header & equalizer
            self.draw_header_and_eq(image)

            # 3. Ambient cyan glow & floating glass card
            self.draw_ambient_rays(image)

            card_box = (42, 132, 1238, 592)
            self.draw_glow_box(
                image,
                card_box,
                radius=38,
                glow_color=(0, 210, 255, 110),
                blur_radius=16,
            )

            card_layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
            cd = ImageDraw.Draw(card_layer)
            cd.rounded_rectangle(
                card_box,
                radius=38,
                fill=self.glass_fill,
                outline=self.glass_border,
                width=3,
            )
            image.alpha_composite(card_layer)

            # 4. Larger glowing cover on the left
            cover_size = (412, 412)
            cover_x, cover_y = 74, 156
            cover_box = (cover_x, cover_y, cover_x + cover_size[0], cover_y + cover_size[1])

            self.draw_glow_box(
                image,
                cover_box,
                radius=30,
                glow_color=(0, 225, 255, 155),
                blur_radius=15,
            )

            cover = ImageOps.fit(
                raw_cover,
                cover_size,
                method=Image.Resampling.LANCZOS,
            )
            cover = self.rounded_cover(cover, radius=28)
            image.alpha_composite(cover, (cover_x, cover_y))

            cover_border = Image.new("RGBA", self.size, (0, 0, 0, 0))
            cbd = ImageDraw.Draw(cover_border)
            cbd.rounded_rectangle(
                cover_box,
                radius=28,
                outline=(120, 235, 255, 210),
                width=3,
            )
            image.alpha_composite(cover_border)

            # 5. Right panel: LIVE VC badge, title, artist, timeline, controls
            ui_layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(ui_layer)

            # Top-right LIVE VC pill badge
            badge_box = (1006, 166, 1196, 216)
            draw.rounded_rectangle(
                badge_box,
                radius=25,
                fill=self.badge_fill,
                outline=(120, 230, 255, 165),
                width=2,
            )
            draw.text(
                (1030, 179),
                "LIVE VC",
                font=self.font_badge,
                fill=self.white,
            )
            draw.ellipse(
                (1156, 184, 1172, 200),
                fill=self.bright_cyan,
            )

            # Song title & artist
            text_left = 526
            text_max_w = 665

            title = self.fit_text(
                draw,
                song.title or "Unknown Song",
                self.font_title,
                text_max_w,
            )
            draw.text(
                (text_left, 238),
                title,
                font=self.font_title,
                fill=self.white,
            )

            channel = str(song.channel_name or "KOAPMUSIC").strip()
            subtitle = self.fit_text(
                draw,
                f"♪  {channel}",
                self.font_subtitle,
                text_max_w,
            )
            draw.text(
                (text_left, 296),
                subtitle,
                font=self.font_subtitle,
                fill=self.muted,
            )

            # Progress bar
            prog_left = 526
            prog_right = 1192
            prog_y = 368
            prog_h = 8

            draw.rounded_rectangle(
                (prog_left, prog_y - prog_h // 2, prog_right, prog_y + prog_h // 2),
                radius=4,
                fill=(130, 175, 215, 95),
            )

            knob_x = prog_left + int((prog_right - prog_left) * 0.42)
            draw.rounded_rectangle(
                (prog_left, prog_y - prog_h // 2, knob_x, prog_y + prog_h // 2),
                radius=4,
                fill=self.cyan,
            )
            draw.ellipse(
                (knob_x - 10, prog_y - 10, knob_x + 10, prog_y + 10),
                fill=self.white,
                outline=self.cyan,
                width=2,
            )

            # Left label & right duration
            draw.text(
                (prog_left, 386),
                "KOAPMUSIC",
                font=self.font_small,
                fill=self.soft_white,
            )

            duration_str = str(song.duration or "00:00")
            dur_w = draw.textbbox((0, 0), duration_str, font=self.font_small)[2]
            draw.text(
                (prog_right - dur_w, 386),
                duration_str,
                font=self.font_small,
                fill=self.soft_white,
            )

            # Transport controls & volume slider
            center_x = (prog_left + prog_right) // 2
            self.draw_transport_controls(draw, center_x, 466)
            self.draw_volume_bar(draw, center_x, 542)

            # 6. Bottom glass footer bar
            footer_box = (42, 616, 1238, 688)
            draw.rounded_rectangle(
                footer_box,
                radius=26,
                fill=self.footer_fill,
                outline=(110, 220, 255, 155),
                width=2,
            )
            draw.text(
                (76, 636),
                "Powered by KOAPMUSIC",
                font=self.font_regular,
                fill=self.white,
            )

            handle_text = "@KoAPmusic_bot"
            handle_w = draw.textbbox((0, 0), handle_text, font=self.font_regular)[2]
            draw.text(
                (1204 - handle_w, 636),
                handle_text,
                font=self.font_regular,
                fill=self.cyan,
            )

            image.alpha_composite(ui_layer)
            image.convert("RGB").save(output, quality=95)

            try:
                os.remove(temp)
            except Exception:
                pass

            return output

        except Exception as e:
            print(f"Thumbnail generation error: {e}")
            return config.DEFAULT_THUMB
