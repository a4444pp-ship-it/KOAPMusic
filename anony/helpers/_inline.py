# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import types

from anony import app, config, lang
from anony.core.lang import lang_codes
from anony.helpers._premium_emoji import BLANK_BTN_TEXT, pbtn


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [[pbtn(text=text, emoji="TRASH", style="DANGER", callback_data="cancel_dl")]]
        )

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []

        if status:
            keyboard.append(
                [
                    pbtn(
                        text=status,
                        emoji="PLAY_CIRCLE",
                        style="PRIMARY",
                        callback_data=f"controls status {chat_id}",
                    )
                ]
            )
        elif timer:
            keyboard.append(
                [
                    pbtn(
                        text=timer,
                        emoji="TIMER",
                        style="SUCCESS",
                        callback_data=f"controls status {chat_id}",
                    )
                ]
            )

        if not remove:
            keyboard.append(
                [
                    pbtn(
                        text=BLANK_BTN_TEXT,
                        emoji="PLAY_CIRCLE",
                        style="SUCCESS",
                        callback_data=f"controls resume {chat_id}",
                    ),
                    pbtn(
                        text=BLANK_BTN_TEXT,
                        emoji="MUSIC_OFF",
                        style="PRIMARY",
                        callback_data=f"controls pause {chat_id}",
                    ),
                    pbtn(
                        text=BLANK_BTN_TEXT,
                        emoji="LOOP",
                        style="PRIMARY",
                        callback_data=f"controls replay {chat_id}",
                    ),
                    pbtn(
                        text=BLANK_BTN_TEXT,
                        emoji="SPEED",
                        style="PRIMARY",
                        callback_data=f"controls skip {chat_id}",
                    ),
                    pbtn(
                        text=BLANK_BTN_TEXT,
                        emoji="STOP_CIRCLE",
                        style="DANGER",
                        callback_data=f"controls stop {chat_id}",
                    ),
                ]
            )

        keyboard.append(
            [
                pbtn(
                    text="Close",
                    emoji="TRASH",
                    style="DANGER",
                    callback_data=f"controls close {chat_id}",
                )
            ]
        )

        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    pbtn(
                        text=_lang["back"],
                        emoji="FORWARD",
                        style="PRIMARY",
                        callback_data="help back",
                    ),
                    pbtn(
                        text=_lang["close"],
                        emoji="TRASH",
                        style="DANGER",
                        callback_data="help close",
                    ),
                ]
            ]
        else:
            # 3-column grid: keep plain text without icons so labels never clip on mobile
            cbs = ["admins", "auth", "blist", "lang", "ping", "play", "queue", "stats", "sudo"]
            buttons = [
                self.ikb(text=_lang[f"help_{i}"], callback_data=f"help {cb}")
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
            rows.append(
                [
                    pbtn(
                        text=_lang["close"],
                        emoji="TRASH",
                        style="DANGER",
                        callback_data="help close",
                    )
                ]
            )

        return self.ikm(rows)

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            pbtn(
                text=f"{name} ({code})",
                emoji="VERIFIED",
                style="SUCCESS",
                callback_data=f"lang_change {code}",
            )
            if code == _lang
            else self.ikb(
                text=f"{name} ({code})",
                callback_data=f"lang_change {code}",
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [[pbtn(text=text, emoji="CHAT_BUBBLE", style="PRIMARY", url=config.SUPPORT_CHAT)]]
        )

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    pbtn(
                        text=_text,
                        emoji="PLAY_CIRCLE",
                        style="SUCCESS",
                        callback_data=f"controls force {chat_id} {item_id}",
                    )
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        return self.ikm(
            [
                [
                    pbtn(
                        text=_text,
                        emoji="MUSIC_OFF" if playing else "PLAY_CIRCLE",
                        style="PRIMARY" if playing else "SUCCESS",
                        callback_data=f"controls {_action} {chat_id} q",
                    )
                ]
            ]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    pbtn(
                        text=lang["play_mode"],
                        emoji="SETTINGS",
                        style="PRIMARY",
                        callback_data="settings",
                    ),
                    pbtn(
                        text="Enabled" if admin_only else "Disabled",
                        emoji="VERIFIED" if admin_only else "STOP_CIRCLE",
                        style="SUCCESS" if admin_only else "DANGER",
                        callback_data="settings play",
                    ),
                ],
                [
                    pbtn(
                        text=lang["cmd_delete"],
                        emoji="TRASH",
                        style="PRIMARY",
                        callback_data="settings",
                    ),
                    pbtn(
                        text="Enabled" if cmd_delete else "Disabled",
                        emoji="VERIFIED" if cmd_delete else "STOP_CIRCLE",
                        style="SUCCESS" if cmd_delete else "DANGER",
                        callback_data="settings delete",
                    ),
                ],
                [
                    pbtn(
                        text=lang["language"],
                        emoji="SETTINGS",
                        style="PRIMARY",
                        callback_data="settings",
                    ),
                    pbtn(
                        text=lang_codes[language],
                        emoji="VERIFIED",
                        style="PRIMARY",
                        callback_data="language",
                    ),
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                pbtn(
                    text="Add Me To Your Group",
                    emoji="ROBOT",
                    style="SUCCESS",
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [
                pbtn(
                    text="Support",
                    emoji="CHAT_BUBBLE",
                    style="PRIMARY",
                    url="https://t.me/koapsupport",
                ),
                pbtn(
                    text="Channel",
                    emoji="MEGAPHONE",
                    style="PRIMARY",
                    url="https://t.me/cutelover666",
                ),
            ],
        ]

        if private:
            rows.append(
                [
                    pbtn(
                        text="Help",
                        emoji="GRID_MENU",
                        style="PRIMARY",
                        callback_data="help",
                    ),
                    pbtn(
                        text="Owner",
                        emoji="CROWN",
                        style="DANGER",
                        url="https://t.me/AP109110",
                    ),
                ]
            )
        else:
            rows.append(
                [
                    pbtn(
                        text="Help",
                        emoji="GRID_MENU",
                        style="PRIMARY",
                        callback_data="help",
                    ),
                    pbtn(
                        text="Language",
                        emoji="SETTINGS",
                        style="PRIMARY",
                        callback_data="language",
                    ),
                ]
            )

        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    pbtn(text="Copy Link", emoji="LINK", style="PRIMARY", copy_text=link),
                    pbtn(text="YouTube", emoji="YOUTUBE", style="DANGER", url=link),
                ],
            ]
        )
