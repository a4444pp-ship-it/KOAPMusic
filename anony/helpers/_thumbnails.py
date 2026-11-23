# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
from typing import Any
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
        self.light_blue = (145, 215, 255)
        self.white = (248, 252, 255)
        self.soft_white = (225, 238, 248)
        self.muted = (175, 205, 232)

        self.glass_fill = (8, 28, 66, 138)
        self.glass_border = (120, 225, 255, 165)
        self.badge_fill = (16, 62, 118, 175)
        self.footer_fill = (6, 22, 54, 145)

        try:
            self.font_logo = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 64
            )
            self.font_title = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 36
            )
            self.font_subtitle = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 23
            )
            self.font_badge = ImageFont.truetype(
                "anony/helpers/Raleway-Bold.ttf", 18
            )
            self.font_regular = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 19
            )
            self.font_small = ImageFont.truetype(
                "anony/helpers/Inter-Light.ttf", 17
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

    def format_views(self, views: Any) -> str:
        if views is None or views == "":
            return "Views: N/A"

        raw = str(views).strip()
        if raw.lower().startswith("views:"):
            raw = raw.split(":", 1)[1].strip()

        cleaned = raw.replace(",", "").replace(" ", "")
        try:
            num = int(float(cleaned))
        except (ValueError, TypeError):
            return f"Views: {raw}"

        if num < 0:
            return "Views: N/A"
        if num >= 1_000_000_000:
            return f"Views: {num / 1_000_000_000:.1f}B"
        if num >= 1_000_000:
            return f"Views: {num / 1_000_000:.1f}M"
        if num >= 1_000:
            return f"Views: {num / 1_000:.1f}K"
        return f"Views: {num}"

    def _get_song_views(self, song: Track) -> str:
        for attr in ("views", "view_count", "view"):
            val = getattr(song, attr, None)
            if val is not None and val != "":
                return self.format_views(val)
        return "Views: N/A"

    def rounded_cover(self, image: Image.Image, radius: int = 22) -> Image.Image:
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
        radius: int = 32,
        glow_color: tuple[int, int, int, int] = (0, 210, 255, 95),
        blur_radius: int = 16,
    ) -> None:
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.rounded_rectangle(
            box,
            radius=radius,
            outline=glow_color,
            width=6,
        )
        glow = glow.filter(ImageFilter.GaussianBlur(blur_radius))
        image.alpha_composite(glow)

    def draw_ambient_rays(self, image: Image.Image) -> None:
        rays = Image.new("RGBA", image.size, (0, 0, 0, 0))
        rd = ImageDraw.Draw(rays)

        rd.ellipse((160, 110, 1120, 210), fill=(0, 200, 255, 28))
        rd.ellipse((200, 520, 1080, 610), fill=(0, 170, 255, 24))
        rd.rounded_rectangle((240, 142, 1040, 147), radius=2, fill=(120, 235, 255, 65))
        rd.rounded_rectangle((280, 565, 1000, 570), radius=2, fill=(120, 235, 255, 55))

        rays = rays.filter(ImageFilter.GaussianBlur(14))
        image.alpha_composite(rays)

    def draw_airpods_badge(
        self, draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int
    ) -> None:
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=(y1 - y0) // 2,
            fill=self.badge_fill,
            outline=self.glass_border,
            width=2,
        )

        # Left & right AirPods icon
        cy = (y0 + y1) // 2
        lx = x0 + 18
        rx = lx + 20
        top_y = cy - 12

        draw.ellipse((lx, top_y, lx + 12, top_y + 15), outline=self.light_blue, width=2)
        draw.rounded_rectangle((lx + 8, top_y + 11, lx + 12, top_y + 25), radius=2, fill=self.light_blue)

        draw.ellipse((rx, top_y, rx + 12, top_y + 15), outline=self.light_blue, width=2)
        draw.rounded_rectangle((rx, top_y + 11, rx + 4, top_y + 25), radius=2, fill=self.light_blue)

        draw.text(
            (rx + 20, y0 + 11),
            "AirPods",
            font=self.font_badge,
            fill=self.light_blue,
        )

    def draw_header_and_eq(self, image: Image.Image) -> None:
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        # Top-left larger KOAPMusic branding
        draw.text(
            (52, 20),
            "KOAPMusic",
            font=self.font_logo,
            fill=self.white,
            stroke_width=2,
            stroke_fill=(0, 95, 210),
        )
        draw.text(
            (56, 92),
            "TELEGRAM MUSIC BOT",
            font=self.font_small,
            fill=self.bright_cyan,
        )

        # Top-right AirPods badge (waveform removed)
        w, _ = self.size
        self.draw_airpods_badge(draw, w - 238, 36, w - 52, 82)

        image.alpha_composite(layer)

    def draw_transport_controls(
        self, draw: ImageDraw.ImageDraw, center_x: int, center_y: int
    ) -> None:
        # Compact center Play/Pause button
        r = 36
        draw.ellipse(
            (center_x - r, center_y - r, center_x + r, center_y + r),
            fill=(25, 78, 138, 165),
            outline=(140, 235, 255, 180),
            width=2,
        )

        # Pause bars (compact)
        bar_w = 7
        bar_h = 22
        gap = 6
        left_x = center_x - gap - bar_w
        right_x = center_x + gap
        top_y = center_y - bar_h // 2

        draw.rounded_rectangle(
            (left_x, top_y, left_x + bar_w, top_y + bar_h),
            radius=3,
            fill=self.white,
        )
        draw.rounded_rectangle(
            (right_x, top_y, right_x + bar_w, top_y + bar_h),
            radius=3,
            fill=self.white,
        )

        # Previous (<<)
        prev_x = center_x - 100
        draw.polygon(
            [
                (prev_x, center_y - 12),
                (prev_x, center_y + 12),
                (prev_x - 16, center_y),
            ],
            fill=self.soft_white,
        )
        draw.polygon(
            [
                (prev_x + 15, center_y - 12),
                (prev_x + 15, center_y + 12),
                (prev_x - 1, center_y),
            ],
            fill=self.soft_white,
        )

        # Next (>>)
        next_x = center_x + 100
        draw.polygon(
            [
                (next_x, center_y - 12),
                (next_x, center_y + 12),
                (next_x + 16, center_y),
            ],
            fill=self.soft_white,
        )
        draw.polygon(
            [
                (next_x - 15, center_y - 12),
                (next_x - 15, center_y + 12),
                (next_x + 1, center_y),
            ],
            fill=self.soft_white,
        )

    def draw_volume_bar(
        self, draw: ImageDraw.ImageDraw, center_x: int, y: int
    ) -> None:
        # Compact speaker icon
        spk_x = center_x - 118
        draw.polygon(
            [
                (spk_x - 7, y - 4),
                (spk_x - 1, y - 4),
                (spk_x + 6, y - 10),
                (spk_x + 6, y + 10),
                (spk_x - 1, y + 4),
                (spk_x - 7, y + 4),
            ],
            fill=self.soft_white,
        )

        # Compact volume slider track
        bar_left = center_x - 96
        bar_right = center_x + 96
        bar_h = 5
        draw.rounded_rectangle(
            (bar_left, y - bar_h // 2, bar_right, y + bar_h // 2),
            radius=3,
            fill=(160, 200, 235, 105),
        )

        fill_x = bar_left + int((bar_right - bar_left) * 0.62)
        draw.rounded_rectangle(
            (bar_left, y - bar_h // 2, fill_x, y + bar_h // 2),
            radius=3,
            fill=self.cyan,
        )

        knob_r = 7
        draw.ellipse(
            (fill_x - knob_r, y - knob_r, fill_x + knob_r, y + knob_r),
            fill=self.white,
            outline=self.cyan,
            width=2,
        )

        # Sound wave arcs
        wave_x = center_x + 112
        draw.arc(
            (wave_x - 6, y - 6, wave_x + 4, y + 6),
            start=-55,
            end=55,
            fill=self.bright_cyan,
            width=2,
        )
        draw.arc(
            (wave_x - 9, y - 10, wave_x + 9, y + 10),
            start=-55,
            end=55,
            fill=self.bright_cyan,
            width=2,
        )

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            self.size = size
            w, h = self.size

            os.makedirs("cache", exist_ok=True)

            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_koap.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            raw_cover = Image.open(temp).convert("RGB")

            # 1. Blurred cover background + light blue tint (cover silhouette clearly visible)
            bg = ImageOps.fit(
                raw_cover,
                self.size,
                method=Image.Resampling.LANCZOS,
            ).filter(ImageFilter.GaussianBlur(24))
            bg = ImageEnhance.Brightness(bg).enhance(0.62)
            bg = ImageEnhance.Color(bg).enhance(1.22)
            image = bg.convert("RGBA")

            light_blue_tint = Image.new("RGBA", self.size, (16, 78, 152, 72))
            image.alpha_composite(light_blue_tint)

            # 2. Header & AirPods badge
            self.draw_header_and_eq(image)

            # 3. Ambient glow & compact floating glass card
            self.draw_ambient_rays(image)

            card_box = (52, 162, w - 52, h - 78)
            self.draw_glow_box(
                image,
                card_box,
                radius=34,
                glow_color=(0, 210, 255, 85),
                blur_radius=14,
            )

            card_layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
            cd = ImageDraw.Draw(card_layer)
            cd.rounded_rectangle(
                card_box,
                radius=34,
                fill=self.glass_fill,
                outline=self.glass_border,
                width=2,
            )
            image.alpha_composite(card_layer)

            # 4. Small 16:9 cover photo on the left
            cover_size = (448, 252)
            cover_x, cover_y = 84, 244
            cover_box = (
                cover_x,
                cover_y,
                cover_x + cover_size[0],
                cover_y + cover_size[1],
            )

            self.draw_glow_box(
                image,
                cover_box,
                radius=24,
                glow_color=(0, 225, 255, 125),
                blur_radius=12,
            )

            cover = ImageOps.fit(
                raw_cover,
                cover_size,
                method=Image.Resampling.LANCZOS,
            )
            cover = self.rounded_cover(cover, radius=22)
            image.alpha_composite(cover, (cover_x, cover_y))

            cover_border = Image.new("RGBA", self.size, (0, 0, 0, 0))
            cbd = ImageDraw.Draw(cover_border)
            cbd.rounded_rectangle(
                cover_box,
                radius=22,
                outline=(120, 235, 255, 195),
                width=2,
            )
            image.alpha_composite(cover_border)

            # 5. Right panel: compact badge, title, artist, timeline, controls
            ui_layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(ui_layer)

            right_x = 572
            right_max_w = w - right_x - 92

            # Compact LIVE VC pill badge
            badge_box = (w - 238, 192, w - 88, 232)
            draw.rounded_rectangle(
                badge_box,
                radius=20,
                fill=self.badge_fill,
                outline=(120, 230, 255, 155),
                width=2,
            )
            draw.text(
                (w - 216, 202),
                "LIVE VC",
                font=self.font_badge,
                fill=self.white,
            )
            draw.ellipse(
                (w - 118, 205, w - 104, 219),
                fill=self.bright_cyan,
            )

            # Song title & channel (scaled down & clean)
            title = self.fit_text(
                draw,
                song.title or "Unknown Song",
                self.font_title,
                right_max_w,
            )
            draw.text(
                (right_x, 248),
                title,
                font=self.font_title,
                fill=self.white,
            )

            channel = str(song.channel_name or "KOAPMusic").strip()
            subtitle = self.fit_text(
                draw,
                f"♪  {channel}",
                self.font_subtitle,
                right_max_w,
            )
            draw.text(
                (right_x, 296),
                subtitle,
                font=self.font_subtitle,
                fill=self.muted,
            )

            # Compact progress bar
            prog_left = right_x
            prog_right = w - 88
            prog_y = 356
            prog_h = 6

            draw.rounded_rectangle(
                (prog_left, prog_y - prog_h // 2, prog_right, prog_y + prog_h // 2),
                radius=3,
                fill=(130, 175, 215, 95),
            )

            knob_x = prog_left + int((prog_right - prog_left) * 0.42)
            draw.rounded_rectangle(
                (prog_left, prog_y - prog_h // 2, knob_x, prog_y + prog_h // 2),
                radius=3,
                fill=self.cyan,
            )
            draw.ellipse(
                (knob_x - 8, prog_y - 8, knob_x + 8, prog_y + 8),
                fill=self.white,
                outline=self.cyan,
                width=2,
            )

            # Left light-blue KOAPMusic label & right duration + dynamic views
            draw.text(
                (prog_left, 372),
                "KOAPMusic",
                font=self.font_small,
                fill=self.light_blue,
            )

            duration_str = str(song.duration or "00:00")
            dur_w = draw.textbbox((0, 0), duration_str, font=self.font_small)[2]
            draw.text(
                (prog_right - dur_w, 372),
                duration_str,
                font=self.font_small,
                fill=self.soft_white,
            )

            views_str = self._get_song_views(song)
            views_w = draw.textbbox((0, 0), views_str, font=self.font_small)[2]
            draw.text(
                (prog_right - views_w, 396),
                views_str,
                font=self.font_small,
                fill=self.light_blue,
            )

            # Compact transport controls & volume slider
            center_x = (prog_left + prog_right) // 2
            self.draw_transport_controls(draw, center_x, 444)
            self.draw_volume_bar(draw, center_x, 504)

            # 6. Bottom corner credits (left & right corners)
            credit_y = h - 38
            left_credit = "Powered by KOAP Music @ KoAPmusic_bot"
            right_credit = "Created By KOAP @AP109110"

            draw.text(
                (56, credit_y),
                left_credit,
                font=self.font_regular,
                fill=self.soft_white,
            )

            rc_w = draw.textbbox((0, 0), right_credit, font=self.font_regular)[2]
            draw.text(
                (w - 56 - rc_w, credit_y),
                right_credit,
                font=self.font_regular,
                fill=self.bright_cyan,
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
