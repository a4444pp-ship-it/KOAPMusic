# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import types

from anony import app, config, lang
from anony.core.lang import lang_codes


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [self.ikb(text=text, callback_data="cancel_dl", style="danger")]
        ])

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
        autoplay: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []

        if status:
            keyboard.append([
                self.ikb(
                    text=status,
                    callback_data=f"controls status {chat_id}",
                    style="primary",
                )
            ])
        elif timer:
            keyboard.append([
                self.ikb(
                    text=timer,
                    callback_data=f"controls status {chat_id}",
                    style="primary",
                )
            ])

        if not remove:
            keyboard.append([
                self.ikb(
                    text="▷",
                    callback_data=f"controls resume {chat_id}",
                    style="success",
                ),
                self.ikb(
                    text="II",
                    callback_data=f"controls pause {chat_id}",
                    style="danger",
                ),
                self.ikb(
                    text="⥁",
                    callback_data=f"controls replay {chat_id}",
                    style="primary",
                ),
                self.ikb(
                    text="‣‣I",
                    callback_data=f"controls skip {chat_id}",
                    style="primary",
                ),
                self.ikb(
                    text="▢",
                    callback_data=f"controls stop {chat_id}",
                    style="danger",
                ),
            ])

        if not remove:
            keyboard.append([
                self.ikb(
                    text=f"AUTOPLAY {'ON' if autoplay else 'OFF'}",
                    callback_data=f"controls autoplay {chat_id}",
                    style="success" if autoplay else "danger",
                )
            ])

        keyboard.append([
            self.ikb(
                text="Close",
                callback_data=f"controls close {chat_id}",
                style="danger",
                icon_custom_emoji_id="6269316311172518259",
            )
        ])

        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    self.ikb(
                        text=_lang["back"],
                        callback_data="help back",
                        style="primary",
                        icon_custom_emoji_id="5258236805890710909",
                    ),
                    self.ikb(
                        text=_lang["close"],
                        callback_data="help close",
                        style="danger",
                        icon_custom_emoji_id="6269316311172518259",
                    ),
                ]
            ]
        else:
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            styles = ["primary", "primary", "danger", "success", "primary", "success", "primary", "primary", "danger"]
            emojis = [
                "5258513401784573443",  # Admin
                "5316727448644103237",  # Auth
                "6044307467070869456",  # Blacklist
                "6285266011528636295",  # Language
                "6046644354481655825",  # Ping
                "5258334469152054985",  # Play
                "6044271071518003692",  # Queue
                "5974235702701853774",  # Starts (Stats)
                "5258334872878980409",  # Sudoers
            ]
            buttons = [
                self.ikb(
                    text=_lang[f"help_{i}"],
                    callback_data=f"help {cb}",
                    style=styles[i % len(styles)],
                    icon_custom_emoji_id=emojis[i],
                )
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]

        return self.ikm(rows)

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            self.ikb(
                text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
                style="success" if code == _lang else "primary",
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [self.ikb(text=text, url=config.SUPPORT_CHAT, style="primary")]
        ])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(
                    text=_text,
                    callback_data=f"controls force {chat_id} {item_id}",
                    style="success",
                    icon_custom_emoji_id="6213026882108002337",
                )
            ]
        ])

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm([
            [
                self.ikb(
                    text=_text,
                    callback_data=f"controls {_action} {chat_id} q",
                    style="danger" if playing else "success",
                )
            ]
        ])

    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(
                    text=lang["play_mode"] + " ➜",
                    callback_data="settings",
                    style="primary",
                ),
                self.ikb(
                    text=admin_only,
                    callback_data="settings play",
                    style="success" if admin_only else "danger",
                ),
            ],
            [
                self.ikb(
                    text=lang["cmd_delete"] + " ➜",
                    callback_data="settings",
                    style="primary",
                ),
                self.ikb(
                    text=cmd_delete,
                    callback_data="settings delete",
                    style="success" if cmd_delete else "danger",
                ),
            ],
            [
                self.ikb(
                    text=lang["language"] + " ➜",
                    callback_data="settings",
                    style="primary",
                ),
                self.ikb(
                    text=lang_codes[language],
                    callback_data="language",
                    style="success",
                ),
            ],
        ])

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self.ikb(
                    text="Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ",
                    url=f"https://t.me/{app.username}?startgroup=true",
                    style="primary",
                    icon_custom_emoji_id="5258362837411045098",
                )
            ],
            [
                self.ikb(
                    text="Hᴇʟᴘ",
                    callback_data="help",
                    style="success",
                    icon_custom_emoji_id="6008258140108231117",
                )
            ],
            [
                self.ikb(
                    text="Sᴜᴘᴘᴏʀᴛ",
                    url="https://t.me/koapsupport",
                    style="primary",
                    icon_custom_emoji_id="5260535596941582167",
                ),
                self.ikb(
                    text="Cʜᴀɴɴᴇʟ",
                    url="https://t.me/cutelover666",
                    style="primary",
                    icon_custom_emoji_id="5260268501515377807",
                ),
            ],
        ]

        if private:
            rows.append([
                self.ikb(
                    text="Oᴡɴᴇʀ",
                    url="https://t.me/AP109110",
                    style="success",
                    icon_custom_emoji_id="5971831809506282660",
                )
            ])
        else:
            rows.append([
                self.ikb(
                    text="Lᴀɴɢᴜᴀɢᴇ",
                    callback_data="language",
                    style="primary",
                    icon_custom_emoji_id="6285266011528636295",
                )
            ])

        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(text="❐", copy_text=link, style="primary"),
                self.ikb(text="Youtube", url=link, style="danger"),
            ],
        ])
