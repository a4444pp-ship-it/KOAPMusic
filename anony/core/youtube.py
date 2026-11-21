# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# Updated for Aoi Music — XENOBOT2 /url/{video_id} API + 3-Tier Fallback

import asyncio
import os
import random
import re
from pathlib import Path

import aiohttp
import yt_dlp
from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils

try:
    from anony import config as _anony_config
except Exception:
    _anony_config = None


DEFAULT_XENO_API_URL = "https://host-repository.vercel.app/harshmanjjhi/xenobot2/url/"

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_URL_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def _get_xeno_api_url() -> str:
    """Resolve XENOBOT2 public audio API URL from config/env, defaulting to DEFAULT_XENO_API_URL."""
    for key in ("XENO_API_URL", "MUSIC_API_URL", "API_URL"):
        val = getattr(_anony_config, key, None) if _anony_config is not None else None
        if not val:
            val = os.getenv(key)
        if val and str(val).strip():
            return str(val).strip().rstrip("/")
    return DEFAULT_XENO_API_URL.rstrip("/")


def _build_xeno_endpoint(base_url: str, video_id: str) -> str:
    """Build final /url/{video_id} endpoint without duplicating /url."""
    clean_base = base_url.strip().rstrip("/")
    if clean_base.endswith("/url"):
        return f"{clean_base}/{video_id}"
    return f"{clean_base}/url/{video_id}"


class DummyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.downloads_dir = Path("downloads")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.xeno_api_url = _get_xeno_api_url()
        self.api_timeout = int(os.getenv("XENO_API_TIMEOUT", "60"))
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def extract_video_id(self, value: str) -> str | None:
        """Extract an 11-character YouTube video ID from a raw ID or YouTube URL."""
        if not value:
            return None
        value = value.strip()
        if _VIDEO_ID_RE.fullmatch(value):
            return value
        match = _URL_VIDEO_ID_RE.search(value)
        if match:
            return match.group(1)
        return None

    async def resolve_video_id(self, value: str) -> str | None:
        """Resolve a raw ID, YouTube URL, or search query into an 11-char video ID."""
        vid = self.extract_video_id(value)
        if vid:
            return vid
        if not value or not value.strip():
            return None
        try:
            _search = VideosSearch(value.strip(), limit=1, with_live=False)
            results = await _search.next()
            if results and results.get("result"):
                candidate = results["result"][0].get("id")
                if candidate and _VIDEO_ID_RE.fullmatch(candidate):
                    return candidate
        except Exception as ex:
            logger.warning("Failed to resolve video ID for %r: %s", value, ex)
        return None

    def get_cookies(self):
        if not self.checked:
            if os.path.isdir(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; cookie fallback disabled.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        os.makedirs(self.cookie_dir, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(await resp.read())
        self.checked = False
        self.cookies.clear()
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass
        return tracks

    def _find_cached_file(self, video_id: str, video: bool) -> str | None:
        exts = ("mp4", "mkv", "webm") if video else ("mp3", "webm", "m4a", "opus")
        for ext in exts:
            candidate = self.downloads_dir / f"{video_id}.{ext}"
            if candidate.is_file() and candidate.stat().st_size > 0:
                return str(candidate)
        return None

    async def _download_via_xeno_api(self, video_id: str) -> str | None:
        """Type 1: Fetch audio directly from XENOBOT2 public API (/url/{video_id}) without cookies."""
        base_url = self.xeno_api_url or _get_xeno_api_url()
        if not base_url:
            return None

        endpoint = _build_xeno_endpoint(base_url, video_id)
        target = self.downloads_dir / f"{video_id}.mp3"
        temp = self.downloads_dir / f"{video_id}.mp3.part"

        timeout = aiohttp.ClientTimeout(total=self.api_timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "XENOBOT2 API returned HTTP %s for %s (%s)",
                            resp.status,
                            video_id,
                            endpoint,
                        )
                        return None

                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    if "application/json" in content_type or "text/html" in content_type:
                        logger.warning(
                            "XENOBOT2 API returned non-audio content-type (%s) for %s",
                            content_type,
                            video_id,
                        )
                        return None

                    total_bytes = 0
                    with open(temp, "wb") as fh:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            if chunk:
                                fh.write(chunk)
                                total_bytes += len(chunk)

            if total_bytes < 1024:
                temp.unlink(missing_ok=True)
                logger.warning("XENOBOT2 API returned empty/invalid audio for %s", video_id)
                return None

            temp.replace(target)
            return str(target)
        except Exception as ex:
            temp.unlink(missing_ok=True)
            logger.warning("XENOBOT2 API download failed for %s: %s", video_id, ex)
            return None

    async def _download_via_ytdlp(
        self,
        video_id: str,
        video: bool = False,
        cookie: str | None = None,
        use_mobile_clients: bool = False,
    ) -> str | None:
        """Run yt-dlp download in a worker thread (used for Type 2 cookieless & Type 3 cookie fallback)."""
        url = self.base + video_id
        base_opts = {
            "outtmpl": str(self.downloads_dir / "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "logger": DummyLogger(),
            "nocheckcertificate": True,
            "remote_components": ["ejs:github"],
        }

        if cookie:
            base_opts["cookiefile"] = cookie

        if use_mobile_clients:
            base_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "ios", "tv_embedded"],
                }
            }

        if video:
            ydl_opts = {
                **base_opts,
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)/best[height<=?720]",
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                "format": "bestaudio[ext=webm][acodec=opus]/bestaudio/best",
            }

        def _run() -> str | None:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        prepared = Path(ydl.prepare_filename(info))
                        if video:
                            mp4_path = prepared.with_suffix(".mp4")
                            if mp4_path.is_file() and mp4_path.stat().st_size > 0:
                                return str(mp4_path)
                        if prepared.is_file() and prepared.stat().st_size > 0:
                            return str(prepared)
            except Exception as ex:
                mode = "cookie" if cookie else "cookieless"
                logger.warning("yt-dlp (%s) failed for %s: %s: %s", mode, video_id, type(ex).__name__, ex)
                return None
            return self._find_cached_file(video_id, video)

        return await asyncio.to_thread(_run)

    async def download(self, video_id: str, video: bool = False) -> str | None:
        """
        Download audio/video using a 3-tier pipeline:
          1. XENOBOT2 Public Audio API (https://host-repository.vercel.app/harshmanjjhi/xenobot2/url/{video_id}) — no cookies
          2. yt-dlp without cookies (android/ios/tv_embedded player clients)
          3. yt-dlp with cookies fallback (if cookies exist in anony/cookies)
        """
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        resolved_id = await self.resolve_video_id(video_id)
        if not resolved_id:
            logger.error("Unable to resolve a valid 11-char YouTube video ID from %r", video_id)
            return None

        cached = self._find_cached_file(resolved_id, video)
        if cached:
            return cached

        # Type 1: XENOBOT2 /url/{video_id} API (audio only, no cookies needed)
        if not video:
            api_file = await self._download_via_xeno_api(resolved_id)
            if api_file:
                return api_file

        # Type 2: Cookieless yt-dlp fallback (when ID not found on XENOBOT2 API or video=True)
        cookieless_file = await self._download_via_ytdlp(
            resolved_id,
            video=video,
            cookie=None,
            use_mobile_clients=True,
        )
        if cookieless_file:
            return cookieless_file

        # Type 3: Cookie-based yt-dlp fallback (only if cookies are available)
        cookie = self.get_cookies()
        if cookie:
            return await self._download_via_ytdlp(
                resolved_id,
                video=video,
                cookie=cookie,
                use_mobile_clients=False,
            )

        logger.error("All 3 download methods failed for %s", resolved_id)
        return None
