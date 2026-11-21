"""
Centralized Telegram Premium (Custom) Emoji registry (59 icons), HTML helpers,
and Bot API 9.4+ InlineKeyboardButton builder for XENOBOT1 (Yumeko) & XENOBOT2.

Supports:
  1. Text / Captions: <tg-emoji emoji-id="...">fallback</tg-emoji> (HTML)
  2. Buttons: icon_custom_emoji_id + style (PRIMARY / SUCCESS / DANGER)
     with full async/sync compatibility for Kurigram 2.2+ and Pyrogram
     (including MTProto raw.types.KeyboardButtonStyle injection).
"""

from __future__ import annotations

import inspect
import logging
import re
from typing import Any, Dict, Optional, Tuple

from pyrogram import enums
from pyrogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)

# Invisible 0px non-whitespace character so icon-only buttons render ONLY the centered premium emoji
BLANK_BTN_TEXT = "\u2060"

# All 59 configured Telegram Premium Custom Emoji IDs: key -> (emoji_id, fallback_emoji)
PREMIUM_EMOJIS: Dict[str, Tuple[str, str]] = {
    # 1-10: Core Audio / Media / Bot
    "MIC_ON": ("5897554554894946515", "🎤"),
    "MIC_OFF": ("5897853622057700958", "🎙"),
    "SPEAKER_ON": ("5890997763331591703", "🔊"),
    "SPEAKER_OFF": ("5890838600433536921", "🔇"),
    "MUSIC_ON": ("5891249688933305846", "🎵"),
    "MUSIC_OFF": ("5890937586544807413", "🎵"),
    "PLAY_CIRCLE": ("5900130736408629854", "🎞"),
    "VIDEO_ON": ("5900130736408629854", "🎞"),
    "STOP_CIRCLE": ("5996789164383669947", "🎞"),
    "VIDEO_OFF": ("5996789164383669947", "🎞"),
    "PLAYLIST": ("5915480455603295660", "🎶"),
    "ROBOT": ("5258093637450866522", "🤖"),
    # 11-20: Search / Nav / Config / Speed / Time / Links
    "SEARCH": ("5874960879434338403", "🔎"),
    "FORWARD": ("5832251986635920010", "➡️"),
    "PIN": ("5276310904445612311", "👇"),
    "SETTINGS": ("6032742198179532882", "⚙"),
    "MUTE": ("5890838600433536921", "🔇"),
    "SPEED": ("5292270487521483627", "↖️"),
    "TIMER": ("5258258882022612173", "⏲"),
    "LOADING": ("6113844439292054570", "⏳"),
    "GIFT": ("5264710902153767489", "🎁"),
    "LINK": ("5240491147779907309", "😛"),
    # 21-35: Comms / Alerts / Users / Docs / Download
    "MAIL": ("5253742260054409879", "✉️"),
    "YOUTUBE": ("5341357385279612709", "😊"),
    "CROSS_BADGE": ("5454350746407419714", "❌"),
    "SPARKLES": ("5454350746407419714", "❌"),
    "CLOCK_24H": ("5366043289633962337", "🕘"),
    "HOURGLASS": ("5373221902267457807", "⏳"),
    "MEGAPHONE": ("4992560350982309130", "📣"),
    "GIFT_ALT": ("5985472565508838112", "🎁"),
    "WARNING": ("5881702736843511327", "⚠️"),
    "USER_BLOCKED": ("5886496611835581345", "👤"),
    "USER": ("5886412370347036129", "👤"),
    "COMPOSE": ("5985774024968379294", "🖊"),
    "PENCIL": ("5879841310902324730", "✏️"),
    "FILE": ("5257965810634202885", "📁"),
    "SEARCH_ALT": ("5874960879434338403", "🔎"),
    "DOWNLOAD": ("6037157012242960559", "⬇️"),
    # 36-46: Live / Play Outline / Loop / Boost / Refresh / EQ / Add Playlist / Done / New
    "LIVE_DOT": ("5778335621491723621", "📷"),
    "PLAY_OUTLINE": ("5775981206319402773", "🎞"),
    "LOOP": ("5877410604225924969", "🔄"),
    "LIGHTNING": ("5843553939672274145", "⚡️"),
    "REFRESH": ("5845943483382110702", "🔄"),
    "EQ_OFF": ("5933629020301169337", "📊"),
    "ADD_PLAYLIST": ("5359529383319084413", "➕"),
    "MUSIC_SINGLE": ("5258334469152054985", "🎶"),
    "DOWNLOAD_TRAY": ("5963087934696459905", "⬇️"),
    "CHECKMARK": ("5823396554345549784", "✔️"),
    "NEW_BADGE": ("5886306834410640699", "🆕"),
    # 47-59: Wave / Anime / Badges / Chat / Grid / Trash / Clover / Crown / Ranks / Gamepad
    "WAVE": ("5260249440450520061", "🤚"),
    "ANIME_WINK": ("5870874364081082158", "😉"),
    "ANIME_COOL": ("5870896319953899581", "😄"),
    "BEST_BADGE": ("5251215200081698759", "👑"),
    "VERIFIED": ("5357069174512303778", "✅"),
    "CHAT_BUBBLE": ("5884179047482659474", "💬"),
    "GRID_MENU": ("5226513232549664618", "🔢"),
    "TRASH": ("5258130763148172425", "🗑"),
    "CLOVER": ("6172537761552142514", "🍀"),
    "CROWN": ("5807868868886009920", "👑"),
    "LEVEL_UP": ("5463122435425448565", "⬆️"),
    "TOP_ICON": ("5463071033256848094", "🔝"),
    "GAMEPAD": ("5938413566624272793", "🎮"),
}

_TG_EMOJI_OPEN_RE = re.compile(
    r"""<tg-emoji\s+emoji-id=(?:"|')?(\d+)(?:"|')?\s*>""",
    re.IGNORECASE,
)
_TG_EMOJI_CLOSE_RE = re.compile(r"</tg-emoji>", re.IGNORECASE)

_IKB_PARAMS: Optional[set] = None
_IKB_ICON_PARAM: Optional[str] = None
_IKB_ICON_IS_INT: bool = False
_PATCHED: bool = False


def _detect_ikb_capabilities() -> None:
    global _IKB_PARAMS, _IKB_ICON_PARAM, _IKB_ICON_IS_INT
    if _IKB_PARAMS is not None:
        return
    try:
        sig = inspect.signature(InlineKeyboardButton.__init__)
        _IKB_PARAMS = set(sig.parameters.keys())
        for candidate in ("icon_custom_emoji_id", "icon", "custom_emoji_id"):
            if candidate in _IKB_PARAMS:
                _IKB_ICON_PARAM = candidate
                ann = sig.parameters[candidate].annotation
                if ann is int or (isinstance(ann, str) and "int" in ann and "str" not in ann):
                    _IKB_ICON_IS_INT = True
                break
    except Exception:
        _IKB_PARAMS = set()
        _IKB_ICON_PARAM = None


def eid(key: str) -> str:
    """Return the raw custom emoji ID string for a registry key (or pass-through numeric ID)."""
    entry = PREMIUM_EMOJIS.get(key)
    if entry:
        return entry[0]
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        return str(key)
    raise KeyError(f"Unknown premium emoji key: {key!r}")


def fallback(key: str) -> str:
    """Return the fallback standard emoji for a registry key."""
    entry = PREMIUM_EMOJIS.get(key)
    return entry[1] if entry else ""


def tg_emoji(key: str, custom_fallback: Optional[str] = None) -> str:
    """Return an HTML <tg-emoji emoji-id="...">fallback</tg-emoji> tag for text/captions."""
    entry = PREMIUM_EMOJIS.get(key)
    if entry:
        emoji_id, fb = entry
        return f'<tg-emoji emoji-id="{emoji_id}">{custom_fallback or fb}</tg-emoji>'
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        return f'<tg-emoji emoji-id="{key}">{custom_fallback or "✨"}</tg-emoji>'
    return custom_fallback or ""


def pe(key: str, custom_fallback: Optional[str] = None) -> str:
    """Short alias for tg_emoji()."""
    return tg_emoji(key, custom_fallback=custom_fallback)


def _normalize_tg_emoji_html(text: Any) -> Any:
    """Convert <tg-emoji emoji-id="...">...</tg-emoji> into Pyrogram/Kurigram <emoji id="...">...</emoji>."""
    if isinstance(text, str) and "<tg-emoji" in text.lower():
        text = _TG_EMOJI_OPEN_RE.sub(r'<emoji id="\1">', text)
        text = _TG_EMOJI_CLOSE_RE.sub("</emoji>", text)
    return text


def _resolve_style(style: Optional[str]) -> Any:
    """Resolve 'PRIMARY' / 'SUCCESS' / 'DANGER' into enums.ButtonStyle if supported."""
    if not style:
        return None
    btn_style_enum = getattr(enums, "ButtonStyle", None)
    if btn_style_enum is None:
        return None
    return getattr(btn_style_enum, str(style).upper(), None)


def pbtn(
    text: str,
    *,
    emoji: Optional[str] = None,
    style: Optional[str] = None,
    **kwargs: Any,
) -> InlineKeyboardButton:
    """
    Build an InlineKeyboardButton with Telegram Bot API 9.4+ custom emoji icon
    (icon_custom_emoji_id) and optional colored button style (PRIMARY/SUCCESS/DANGER).
    """
    _detect_ikb_capabilities()

    btn_kwargs = dict(kwargs)
    resolved_icon: Optional[str] = None
    if emoji:
        try:
            resolved_icon = eid(emoji)
        except KeyError:
            resolved_icon = None

    resolved_style = _resolve_style(style)
    if resolved_style is not None and _IKB_PARAMS and "style" in _IKB_PARAMS:
        btn_kwargs["style"] = resolved_style

    used_native_icon = False
    if resolved_icon and _IKB_ICON_PARAM:
        icon_val: Any = int(resolved_icon) if _IKB_ICON_IS_INT else resolved_icon
        btn_kwargs[_IKB_ICON_PARAM] = icon_val
        used_native_icon = True

    try:
        btn = InlineKeyboardButton(text=text, **btn_kwargs)
    except (TypeError, ValueError):
        if used_native_icon and _IKB_ICON_PARAM in btn_kwargs:
            alt_val = (
                str(resolved_icon)
                if isinstance(btn_kwargs[_IKB_ICON_PARAM], int)
                else int(resolved_icon)
            )
            btn_kwargs[_IKB_ICON_PARAM] = alt_val
            try:
                btn = InlineKeyboardButton(text=text, **btn_kwargs)
            except (TypeError, ValueError):
                btn_kwargs.pop(_IKB_ICON_PARAM, None)
                used_native_icon = False
                try:
                    btn = InlineKeyboardButton(text=text, **btn_kwargs)
                except (TypeError, ValueError):
                    btn_kwargs.pop("style", None)
                    btn = InlineKeyboardButton(text=text, **btn_kwargs)
        else:
            btn_kwargs.pop("style", None)
            btn = InlineKeyboardButton(text=text, **btn_kwargs)

    if resolved_icon and not used_native_icon:
        try:
            setattr(btn, "_pe_icon_id", int(resolved_icon))
            setattr(btn, "_pe_style_name", str(style).upper() if style else None)
        except Exception:
            pass

    return btn


def _inject_raw_button_style(btn_self: Any, raw_btn: Any, kb_style_cls: Any) -> Any:
    """Attach MTProto KeyboardButtonStyle(icon=...) to a serialized raw button if needed."""
    icon_id = getattr(btn_self, "_pe_icon_id", None)
    if icon_id and raw_btn is not None and hasattr(raw_btn, "style"):
        existing = getattr(raw_btn, "style", None)
        style_name = getattr(btn_self, "_pe_style_name", None)
        bg_primary = getattr(existing, "bg_primary", None) or (
            True if style_name == "PRIMARY" else None
        )
        bg_danger = getattr(existing, "bg_danger", None) or (
            True if style_name == "DANGER" else None
        )
        bg_success = getattr(existing, "bg_success", None) or (
            True if style_name == "SUCCESS" else None
        )
        try:
            raw_btn.style = kb_style_cls(
                bg_primary=bg_primary,
                bg_danger=bg_danger,
                bg_success=bg_success,
                icon=int(icon_id),
            )
        except Exception:
            pass
    return raw_btn


def patch_pyrogram_premium_emoji() -> None:
    """
    Install safe, idempotent, async/sync-aware runtime shims for Kurigram & Pyrogram:
      1. Normalizes <tg-emoji emoji-id="..."> into <emoji id="..."> in HTML.parse().
      2. Injects MTProto raw.types.KeyboardButtonStyle(icon=...) in InlineKeyboardButton.write().
    """
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True
    _detect_ikb_capabilities()

    try:
        from pyrogram.parser.html import HTML as PyroHTML

        orig_parse = getattr(PyroHTML, "parse", None)
        if orig_parse and not getattr(orig_parse, "_tg_emoji_patched", False):
            if inspect.iscoroutinefunction(orig_parse):
                async def _patched_html_parse(self, text: str, *args: Any, **kwargs: Any):
                    return await orig_parse(self, _normalize_tg_emoji_html(text), *args, **kwargs)
            else:
                def _patched_html_parse(self, text: str, *args: Any, **kwargs: Any):
                    return orig_parse(self, _normalize_tg_emoji_html(text), *args, **kwargs)

            _patched_html_parse._tg_emoji_patched = True
            PyroHTML.parse = _patched_html_parse
            logger.info("Enabled <tg-emoji> -> <emoji> HTML compatibility shim.")
    except Exception as exc:
        logger.debug("Skipped HTML <tg-emoji> shim: %s", exc)

    try:
        from pyrogram import raw

        kb_style_cls = getattr(raw.types, "KeyboardButtonStyle", None)
        orig_write = getattr(InlineKeyboardButton, "write", None)
        if (
            kb_style_cls is not None
            and orig_write is not None
            and not getattr(orig_write, "_pe_write_patched", False)
        ):
            try:
                style_sig = inspect.signature(kb_style_cls.__init__)
                has_icon_field = "icon" in style_sig.parameters
            except Exception:
                has_icon_field = False

            if has_icon_field:
                if inspect.iscoroutinefunction(orig_write):
                    async def _patched_write(self, *args: Any, **kwargs: Any):
                        raw_btn = await orig_write(self, *args, **kwargs)
                        return _inject_raw_button_style(self, raw_btn, kb_style_cls)
                else:
                    def _patched_write(self, *args: Any, **kwargs: Any):
                        raw_btn = orig_write(self, *args, **kwargs)
                        return _inject_raw_button_style(self, raw_btn, kb_style_cls)

                _patched_write._pe_write_patched = True
                InlineKeyboardButton.write = _patched_write
                logger.info("Enabled MTProto KeyboardButtonStyle icon compatibility shim.")
    except Exception as exc:
        logger.debug("Skipped InlineKeyboardButton.write shim: %s", exc)

    # 3. Kurigram compatibility shim for Pyrofork-only `invert_media` & legacy `disable_web_page_preview`
    try:
        import pyrogram
        from pyrogram import Client as _PyroClient

        lpo_cls = getattr(pyrogram.types, "LinkPreviewOptions", None)

        def _wrap_compat(cls, method_name: str):
            orig = getattr(cls, method_name, None)
            if orig is None or getattr(orig, "_kurigram_compat_patched", False):
                return
            try:
                sig = inspect.signature(orig)
                params = sig.parameters
                has_invert = "invert_media" in params
                has_dwp = "disable_web_page_preview" in params
                accepts_lpo = "link_preview_options" in params
            except Exception:
                has_invert = False
                has_dwp = False
                accepts_lpo = False

            if has_invert and has_dwp:
                return

            async def _wrapped_compat(self, *args, **kwargs):
                inv = kwargs.pop("invert_media", None) if not has_invert else None
                dwp = kwargs.pop("disable_web_page_preview", None) if not has_dwp else None
                if accepts_lpo and lpo_cls is not None and "link_preview_options" not in kwargs:
                    lpo_kwargs = {}
                    if dwp is not None:
                        lpo_kwargs["is_disabled"] = bool(dwp)
                    if inv is not None:
                        lpo_kwargs["show_above_text"] = bool(inv)
                    if lpo_kwargs:
                        try:
                            kwargs["link_preview_options"] = lpo_cls(**lpo_kwargs)
                        except Exception:
                            pass
                return await orig(self, *args, **kwargs)

            _wrapped_compat._kurigram_compat_patched = True
            setattr(cls, method_name, _wrapped_compat)

        for target_cls, methods in (
            (_PyroClient, ("send_message", "edit_message_text")),
            (pyrogram.types.Message, ("reply", "reply_text", "edit", "edit_text")),
            (pyrogram.types.CallbackQuery, ("edit_message_text",)),
        ):
            if target_cls is not None:
                for m in methods:
                    _wrap_compat(target_cls, m)
        logger.info("Enabled Kurigram invert_media / disable_web_page_preview compatibility shim.")
    except Exception as exc:
        logger.debug("Skipped Kurigram invert_media shim: %s", exc)
