# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# Updated for Aoi Music — XENOBOT2 /url/{video_id} API + 3-Tier Fallback

import asyncio
import os
import random
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

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
_PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{2,}$")
_URL_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)
_YT_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
_UNAVAILABLE_TITLES = {
    "[private video]",
    "[deleted video]",
    "[unavailable video]",
    "private video",
    "deleted video",
}


def _get_xeno_api_url() -> str:
    for key in ("XENO_API_URL", "MUSIC_API_URL", "API_URL"):
        val = getattr(_anony_config, key, None) if _anony_config is not None else None
        if not val:
            val = os.getenv(key)
        if val and str(val).strip():
            return str(val).strip().rstrip("/")
    return DEFAULT_XENO_API_URL.rstrip("/")


def _build_xeno_endpoint(base_url: str, video_id: str) -> str:
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
        self.downloads_dir = Path(__file__).resolve().parents[2] / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.xeno_api_url = _get_xeno_api_url()
        self.api_timeout = int(os.getenv("XENO_API_TIMEOUT", "60"))
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?(?:.*&)?(?:v=|list=)|shorts/|live/|embed/|playlist\?(?:.*&)?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{2,})([&?][^\s]*)?"
        )

        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)\S*"
        )

    def _parse_yt_url(self, url: str):
        if not url or not isinstance(url, str):
            return None
        candidate = url.strip()
        if not candidate:
            return None
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        try:
            parsed = urlsplit(candidate)
        except Exception:
            return None
        host = (parsed.hostname or "").lower()
        if host not in _YT_HOSTS:
            return None
        query = parse_qs(parsed.query, keep_blank_values=False)
        return host, parsed.path or "", query

    def extract_video_id(self, value: str) -> str | None:
        if not value:
            return None

        value = value.strip()

        if _VIDEO_ID_RE.fullmatch(value):
            return value

        match = _URL_VIDEO_ID_RE.search(value)

        if match:
            return match.group(1)

        parsed = self._parse_yt_url(value)
        if parsed:
            host, path, query = parsed
            v_vals = query.get("v")
            if v_vals and _VIDEO_ID_RE.fullmatch(v_vals[0]):
                return v_vals[0]
            if host.endswith("youtu.be"):
                seg = path.strip("/").split("/")[0]
                if _VIDEO_ID_RE.fullmatch(seg):
                    return seg

        return None

    def extract_playlist_id(self, value: str) -> str | None:
        parsed = self._parse_yt_url(value)
        if not parsed:
            return None

        _, path, query = parsed
        list_vals = query.get("list")
        if list_vals:
            list_id = list_vals[0].strip()
            if _PLAYLIST_ID_RE.fullmatch(list_id):
                return list_id

        # Support YouTube Music browse playlist links like /browse/VLPL...
        if path.startswith("/browse/VL"):
            candidate = path[len("/browse/VL"):].split("/")[0].strip()
            if _PLAYLIST_ID_RE.fullmatch(candidate):
                return candidate

        return None

    def is_playlist(self, url: str) -> bool:
        return bool(self.extract_playlist_id(url))

    def _normalize_playlist_url(self, url: str) -> tuple[str, str | None]:
        list_id = self.extract_playlist_id(url)
        if not list_id:
            return url, None

        vid = self.extract_video_id(url)
        # Auto-generated YouTube Mixes (RD...) need the seed video id
        if list_id.startswith("RD") and not list_id.startswith("RDCLAK") and vid:
            return f"https://www.youtube.com/watch?v={vid}&list={list_id}", list_id

        return f"https://www.youtube.com/playlist?list={list_id}", list_id

    async def resolve_video_id(self, value: str) -> str | None:
        vid = self.extract_video_id(value)

        if vid:
            return vid

        if not value or not value.strip():
            return None

        try:
            _search = VideosSearch(
                value.strip(),
                limit=1,
                with_live=False
            )

            results = await _search.next()

            if results and results.get("result"):
                candidate = results["result"][0].get("id")

                if candidate and _VIDEO_ID_RE.fullmatch(candidate):
                    return candidate

        except Exception as ex:
            logger.warning(
                "Failed to resolve video ID for %r: %s",
                value,
                ex
            )

        return None

    def get_cookies(self):
        if not self.checked:
            if os.path.isdir(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(
                            f"{self.cookie_dir}/{file}"
                        )

            self.checked = True

        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning(
                    "Cookies are missing; cookie fallback disabled."
                )

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

                    with open(
                        f"{self.cookie_dir}/{name}.txt",
                        "wb"
                    ) as fw:
                        fw.write(await resp.read())

        self.checked = False
        self.cookies.clear()

        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        if not self._parse_yt_url(url):
            return False
        if self.extract_playlist_id(url) or self.extract_video_id(url):
            return True
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        if not self._parse_yt_url(url):
            return False
        return not self.valid(url)

    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False
    ) -> Track | None:

        try:
            _search = VideosSearch(
                query,
                limit=1,
                with_live=False
            )

            results = await _search.next()

        except Exception as ex:
            logger.warning("YouTube search failed: %s", ex)
            return None

        if results and results.get("result"):
            data = results["result"][0]

            thumbnails = data.get("thumbnails") or []
            thumbnail = ""

            if thumbnails:
                thumbnail = (
                    thumbnails[-1].get("url", "").split("?")[0]
                )

            title = data.get("title") or "Unknown Title"

            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration") or "0:00",
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=title[:50],
                thumbnail=thumbnail,
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )

        return None

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str,
        video: bool
    ) -> list[Track]:

        """
        Fetch full YouTube / YouTube Music playlists using:
        1. py_yt Playlist (with pagination)
        2. yt-dlp cookieless flat extraction
        3. yt-dlp cookie fallback

        limit = 0 means unlimited application-level playlist limit.
        """

        target_url, _ = self._normalize_playlist_url(url)
        tracks: list[Track] = []
        seen_ids: set[str] = set()

        def _duration_text(seconds):
            if seconds is None:
                return None

            if isinstance(seconds, str):
                cleaned = seconds.strip()
                if ":" in cleaned:
                    return cleaned

            try:
                seconds = max(0, int(float(seconds)))
            except (TypeError, ValueError):
                return str(seconds) if seconds else None

            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)

            if hours:
                return f"{hours}:{minutes:02d}:{secs:02d}"

            return f"{minutes}:{secs:02d}"

        def _normalise_item(data):
            if not isinstance(data, dict):
                return None

            raw_id = (
                data.get("id")
                or data.get("video_id")
                or data.get("url")
                or data.get("link")
            )
            video_id = self.extract_video_id(str(raw_id or ""))

            if not video_id:
                return None

            title = str(data.get("title") or "Unknown Title").strip()
            if title.lower() in _UNAVAILABLE_TITLES:
                return None

            duration_raw = data.get("duration")
            if duration_raw is None:
                duration_raw = data.get("duration_string")
            duration_text = _duration_text(duration_raw) or "0:00"

            try:
                duration_sec = utils.to_seconds(duration_text)
            except Exception:
                try:
                    duration_sec = int(float(duration_raw or 0))
                except (TypeError, ValueError):
                    duration_sec = 0

            channel = (
                data.get("channel")
                or data.get("uploader")
                or ""
            )

            if isinstance(channel, dict):
                channel = (
                    channel.get("name")
                    or channel.get("title")
                    or ""
                )

            thumbnail = data.get("thumbnail") or ""
            thumbnails = data.get("thumbnails") or []

            if not thumbnail and isinstance(thumbnails, list) and thumbnails:
                last_thumb = thumbnails[-1]
                if isinstance(last_thumb, dict):
                    thumbnail = last_thumb.get("url") or ""

            if not thumbnail:
                thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

            link = f"{self.base}{video_id}"

            return Track(
                id=video_id,
                channel_name=str(channel),
                duration=duration_text,
                duration_sec=duration_sec,
                title=title[:50],
                thumbnail=str(thumbnail).split("?")[0],
                url=link,
                user=user,
                view_count=str(data.get("view_count") or ""),
                video=video,
            )

        def _append_items(items) -> bool:
            for item in items or []:
                if not item:
                    continue
                track = _normalise_item(dict(item) if isinstance(item, dict) else item)
                if track and track.id not in seen_ids:
                    tracks.append(track)
                    seen_ids.add(track.id)
                    if limit and limit > 0 and len(tracks) >= limit:
                        return True
            return False

        # TIER 1: py_yt playlist parser (with continuation pagination)
        try:
            pl = Playlist(target_url)
            if hasattr(pl, "init"):
                await pl.init()

            items = getattr(pl, "videos", None) or []
            reached_limit = _append_items(items)

            pages = 0
            while (
                not reached_limit
                and getattr(pl, "hasMoreVideos", False)
                and hasattr(pl, "getNextVideos")
                and pages < 20
            ):
                pages += 1
                prev_count = len(getattr(pl, "videos", []) or [])
                await pl.getNextVideos()
                current_videos = getattr(pl, "videos", []) or []
                if len(current_videos) <= prev_count:
                    break
                reached_limit = _append_items(current_videos[prev_count:])

            if not tracks:
                playlist_data = await Playlist.get(target_url)
                if isinstance(playlist_data, dict):
                    fallback_items = playlist_data.get("videos") or []
                else:
                    fallback_items = getattr(playlist_data, "videos", None) or []
                _append_items(fallback_items)

            if tracks:
                return tracks

        except Exception as ex:
            logger.warning(
                "py_yt playlist fetch failed (%s): %s",
                type(ex).__name__,
                ex
            )

        # TIER 2 & 3: yt-dlp flat extraction (cookieless -> cookie fallback)
        def _extract_playlist(cookie: str | None = None):
            options = {
                "extract_flat": "in_playlist",
                "noplaylist": False,
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "logger": DummyLogger(),
                "socket_timeout": 20,
                "extractor_retries": 3,
            }

            if cookie:
                options["cookiefile"] = cookie

            if limit and limit > 0:
                options["playlist_items"] = f"1:{limit}"

            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(
                    target_url,
                    download=False
                )

        for use_cookie in (False, True):
            cookie_file = self.get_cookies() if use_cookie else None
            if use_cookie and not cookie_file:
                break

            try:
                info = await asyncio.to_thread(_extract_playlist, cookie_file)
                entries = (info or {}).get("entries") or []
                _append_items(entries)
                if tracks:
                    return tracks
            except Exception as ex:
                mode = "cookie" if cookie_file else "cookieless"
                logger.error(
                    "yt-dlp playlist (%s) failed (%s): %s",
                    mode,
                    type(ex).__name__,
                    ex
                )

        if not tracks:
            logger.error(
                "Unable to extract playlist: %s",
                url
            )

        return tracks

    def _find_cached_file(
        self,
        video_id: str,
        video: bool
    ) -> str | None:

        exts = (
            ("mp4", "mkv", "webm")
            if video
            else ("mp3", "webm", "m4a", "opus")
        )

        for ext in exts:
            candidate = self.downloads_dir / f"{video_id}.{ext}"

            if candidate.is_file() and candidate.stat().st_size > 0:
                return str(candidate)

        return None

    async def _download_via_xeno_api(
        self,
        video_id: str
    ) -> str | None:

        base_url = self.xeno_api_url or _get_xeno_api_url()

        if not base_url:
            return None

        endpoint = _build_xeno_endpoint(
            base_url,
            video_id
        )

        target = self.downloads_dir / f"{video_id}.mp3"
        temp = self.downloads_dir / f"{video_id}.mp3.part"

        timeout = aiohttp.ClientTimeout(
            total=self.api_timeout
        )

        try:
            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.get(endpoint) as resp:

                    if resp.status != 200:
                        logger.warning(
                            "XENOBOT2 API returned HTTP %s for %s (%s)",
                            resp.status,
                            video_id,
                            endpoint
                        )
                        return None

                    content_type = (
                        resp.headers.get("Content-Type") or ""
                    ).lower()

                    if (
                        "application/json" in content_type
                        or "text/html" in content_type
                    ):
                        logger.warning(
                            "XENOBOT2 API returned non-audio content-type (%s) for %s",
                            content_type,
                            video_id
                        )
                        return None

                    total_bytes = 0

                    with open(temp, "wb") as fh:
                        async for chunk in resp.content.iter_chunked(
                            64 * 1024
                        ):
                            if chunk:
                                fh.write(chunk)
                                total_bytes += len(chunk)

            if total_bytes < 1024:
                temp.unlink(missing_ok=True)

                logger.warning(
                    "XENOBOT2 API returned empty/invalid audio for %s",
                    video_id
                )

                return None

            temp.replace(target)

            return str(target)

        except Exception as ex:
            temp.unlink(missing_ok=True)

            logger.warning(
                "XENOBOT2 API download failed for %s: %s",
                video_id,
                ex
            )

            return None

    async def _download_via_ytdlp(
        self,
        video_id: str,
        video: bool = False,
        cookie: str | None = None,
        use_mobile_clients: bool = False,
    ) -> str | None:

        url = self.base + video_id

        base_opts = {
            "outtmpl": str(
                self.downloads_dir / "%(id)s.%(ext)s"
            ),
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
                    "player_client": [
                        "android",
                        "ios",
                        "tv_embedded"
                    ],
                }
            }

        if video:
            ydl_opts = {
                **base_opts,
                "format": (
                    "(bestvideo[height<=?720][width<=?1280][ext=mp4])"
                    "+(bestaudio)/best[height<=?720]"
                ),
                "merge_output_format": "mp4",
            }

        else:
            ydl_opts = {
                **base_opts,
                "format": (
                    "bestaudio[ext=webm][acodec=opus]"
                    "/bestaudio/best"
                ),
            }

        def _run() -> str | None:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                    info = ydl.extract_info(
                        url,
                        download=True
                    )

                    if info:
                        prepared = Path(
                            ydl.prepare_filename(info)
                        )

                        if video:
                            mp4_path = prepared.with_suffix(".mp4")

                            if (
                                mp4_path.is_file()
                                and mp4_path.stat().st_size > 0
                            ):
                                return str(mp4_path)

                        if (
                            prepared.is_file()
                            and prepared.stat().st_size > 0
                        ):
                            return str(prepared)

            except Exception as ex:
                mode = "cookie" if cookie else "cookieless"

                logger.warning(
                    "yt-dlp (%s) failed for %s: %s: %s",
                    mode,
                    video_id,
                    type(ex).__name__,
                    ex
                )

                return None

            return self._find_cached_file(
                video_id,
                video
            )

        return await asyncio.to_thread(_run)

    async def download(
        self,
        video_id: str,
        video: bool = False
    ) -> str | None:

        """
        Download audio/video using a 3-tier pipeline:

        1. XENOBOT2 Public Audio API
        2. yt-dlp without cookies
        3. yt-dlp with cookies fallback
        """

        self.downloads_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        resolved_id = await self.resolve_video_id(
            video_id
        )

        if not resolved_id:
            logger.error(
                "Unable to resolve a valid 11-char YouTube Video ID from %r",
                video_id
            )
            return None

        cached = self._find_cached_file(
            resolved_id,
            video
        )

        if cached:
            return cached

        # TIER 1: XENOBOT2 API

        if not video:
            api_file = await self._download_via_xeno_api(
                resolved_id
            )

            if api_file:
                return api_file

        # TIER 2: yt-dlp without cookies

        cookieless_file = await self._download_via_ytdlp(
            resolved_id,
            video=video,
            cookie=None,
            use_mobile_clients=True,
        )

        if cookieless_file:
            return cookieless_file

        # TIER 3: yt-dlp with cookies

        cookie = self.get_cookies()

        if cookie:
            return await self._download_via_ytdlp(
                resolved_id,
                video=video,
                cookie=cookie,
                use_mobile_clients=False,
            )

        logger.error(
            "All 3 download methods failed for %s",
            resolved_id
        )

        return None
