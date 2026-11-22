import asyncio
from time import time
from typing import Dict, List, Union

import requests
from pykeyboard import InlineKeyboard
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtube_search import YoutubeSearch

from anony import anon, app, config, db, lang, queue, yt

# Define a dictionary to track the last message timestamp for each user
user_last_message_time = {}
user_command_count = {}
# Define the threshold for command spamming (e.g., 20 commands within 60 seconds)
SPAM_THRESHOLD = 2
SPAM_WINDOW_SECONDS = 5

playlistdb = getattr(db, "playlist", None)
if playlistdb is None and hasattr(db, "db"):
    playlistdb = db.db.playlist
elif playlistdb is None and hasattr(db, "client"):
    playlistdb = db.client.get_default_database().playlist

playlist = []
# Playlist Databse

SERVER_PLAYLIST_LIMIT = getattr(config, "SERVER_PLAYLIST_LIMIT", 150)


def _get_lang_dict(code: str = "en") -> dict:
    for attr in ("strings", "data", "languages", "lang_dict"):
        d = getattr(lang, attr, None)
        if isinstance(d, dict) and d:
            return d.get(code) or next(iter(d.values()), {})
    return {}


def _get_strings(message_or_cb) -> dict:
    user = getattr(message_or_cb, "from_user", None)
    code = getattr(user, "language_code", None) or "en"
    return _get_lang_dict(code)


async def _get_playlists(chat_id: int) -> Dict[str, dict]:
    if playlistdb is None:
        return {}
    _notes = await playlistdb.find_one({"chat_id": chat_id})
    if not _notes:
        return {}
    return _notes.get("notes", {})


async def get_playlist_names(chat_id: int) -> List[str]:
    _notes = await _get_playlists(chat_id)
    return list(_notes.keys())


async def get_playlist(chat_id: int, name: str) -> Union[bool, dict]:
    _notes = await _get_playlists(chat_id)
    if name in _notes:
        return _notes[name]
    return False


async def save_playlist(chat_id: int, name: str, note: dict):
    if playlistdb is None:
        return
    _notes = await _get_playlists(chat_id)
    _notes[name] = note
    await playlistdb.update_one(
        {"chat_id": chat_id}, {"$set": {"notes": _notes}}, upsert=True
    )


async def delete_playlist(chat_id: int, name: str) -> bool:
    if playlistdb is None:
        return False
    notesd = await _get_playlists(chat_id)
    if name in notesd:
        del notesd[name]
        await playlistdb.update_one(
            {"chat_id": chat_id},
            {"$set": {"notes": notesd}},
            upsert=True,
        )
        return True
    return False


def _bl_filter():
    bl = getattr(app, "bl_users", None)
    if bl is not None:
        try:
            return ~bl
        except Exception:
            pass
    return filters.all


BL_FILTER = _bl_filter()

# Command
ADDPLAYLIST_COMMAND = "addplaylist"
PLAYLIST_COMMAND = "playlist"
DELETEPLAYLIST_COMMAND = "delplaylist"
DELETE_ALL_PLAYLIST_COMMAND = "delallplaylist"


@app.on_message(filters.command(PLAYLIST_COMMAND) & BL_FILTER)
async def check_playlist(client, message: Message):
    _ = _get_strings(message)
    user_id = message.from_user.id
    current_time = time()
    last_message_time = user_last_message_time.get(user_id, 0)

    if current_time - last_message_time < SPAM_WINDOW_SECONDS:
        user_last_message_time[user_id] = current_time
        user_command_count[user_id] = user_command_count.get(user_id, 0) + 1
        if user_command_count[user_id] > SPAM_THRESHOLD:
            hu = await message.reply_text(
                f"**{message.from_user.mention} ᴘʟᴇᴀsᴇ ᴅᴏɴᴛ ᴅᴏ sᴘᴀᴍ, ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴀғᴛᴇʀ 5 sᴇᴄ**"
            )
            await asyncio.sleep(3)
            await hu.delete()
            return
    else:
        user_command_count[user_id] = 1
        user_last_message_time[user_id] = current_time

    _playlist = await get_playlist_names(message.from_user.id)
    if _playlist:
        get = await message.reply_text(_.get("playlist_2", "Fetching playlist..."))
    else:
        return await message.reply_text(_.get("playlist_3", "Playlist is empty."))

    msg = _.get("playlist_4", "<b>Playlist:</b>\n")
    count = 0
    for shikhar in _playlist:
        _note = await get_playlist(message.from_user.id, shikhar)
        if not isinstance(_note, dict):
            continue
        title = str(_note.get("title", shikhar)).title()
        duration = _note.get("duration", "N/A")
        count += 1
        msg += f"\n\n{count}- {title[:70]}\n"
        msg += _.get("playlist_5", "Duration: {}").format(duration)

    await get.delete()
    if len(msg) > 4000:
        msg = msg[:3950] + "\n..."
    await message.reply_text(msg)


async def get_keyboard(_, user_id):
    keyboard = InlineKeyboard(row_width=5)
    _playlist = await get_playlist_names(user_id)
    count = len(_playlist)
    for x in _playlist:
        _note = await get_playlist(user_id, x)
        title = str(_note.get("title", x)).title() if isinstance(_note, dict) else str(x)
        keyboard.row(
            InlineKeyboardButton(
                text=title[:35],
                callback_data=f"del_playlist {x}",
            )
        )
    keyboard.row(
        InlineKeyboardButton(
            text=_.get("PL_B_5", "Delete All"),
            callback_data="delete_warning",
        ),
        InlineKeyboardButton(
            text=_.get("CLOSE_BUTTON", "Close"),
            callback_data="close",
        ),
    )
    return keyboard, count


@app.on_message(filters.command(DELETEPLAYLIST_COMMAND) & BL_FILTER)
async def del_plist_msg(client, message: Message):
    _ = _get_strings(message)
    user_id = message.from_user.id
    current_time = time()
    last_message_time = user_last_message_time.get(user_id, 0)

    if current_time - last_message_time < SPAM_WINDOW_SECONDS:
        user_last_message_time[user_id] = current_time
        user_command_count[user_id] = user_command_count.get(user_id, 0) + 1
        if user_command_count[user_id] > SPAM_THRESHOLD:
            hu = await message.reply_text(
                f"**{message.from_user.mention} ᴘʟᴇᴀsᴇ ᴅᴏɴᴛ ᴅᴏ sᴘᴀᴍ, ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴀғᴛᴇʀ 5 sᴇᴄ**"
            )
            await asyncio.sleep(3)
            await hu.delete()
            return
    else:
        user_command_count[user_id] = 1
        user_last_message_time[user_id] = current_time

    _playlist = await get_playlist_names(message.from_user.id)
    if _playlist:
        get = await message.reply_text(_.get("playlist_2", "Loading..."))
    else:
        return await message.reply_text(_.get("playlist_3", "Playlist is empty."))
    keyboard, count = await get_keyboard(_, message.from_user.id)
    await get.edit_text(
        _.get("playlist_7", "Total songs: {}").format(count), reply_markup=keyboard
    )


async def _enqueue_and_play(client, chat_id: int, user_id: int, user_name: str, vidids: list, video: bool, mystic: Message):
    added = 0
    for vid in vidids:
        try:
            if hasattr(yt, "details"):
                title, duration_min, duration_sec, thumb_url, vidid = await yt.details(vid, True)
            else:
                title, duration_min, duration_sec, thumb_url, vidid = (
                    str(vid),
                    "0:00",
                    0,
                    f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg",
                    str(vid),
                )
            file_path = None
            if hasattr(yt, "download"):
                file_path = await yt.download(vidid, video=video)
            track = {
                "title": title,
                "dur": duration_min,
                "duration": duration_sec,
                "vidid": vidid,
                "user": user_name,
                "user_id": user_id,
                "file_path": file_path,
                "video": video,
            }
            if hasattr(queue, "add"):
                queue.add(chat_id, track)
            if added == 0 and file_path and hasattr(anon, "play_media"):
                await anon.play_media(chat_id, file_path, video=video)
            added += 1
        except Exception:
            continue
    if added == 0:
        raise RuntimeError("No playable tracks found in playlist.")


@app.on_callback_query(filters.regex("play_playlist") & BL_FILTER)
async def play_playlist(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    callback_data = CallbackQuery.data.strip()
    parts = callback_data.split(None, 1)
    mode = parts[1] if len(parts) > 1 else "a"
    user_id = CallbackQuery.from_user.id
    _playlist = await get_playlist_names(user_id)
    if not _playlist:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_3", "Playlist is empty."), show_alert=True
            )
        except Exception:
            return
    chat_id = CallbackQuery.message.chat.id
    user_name = CallbackQuery.from_user.first_name
    await CallbackQuery.message.delete()
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
    video = True if mode == "v" else False
    mystic = await CallbackQuery.message.reply_text(_.get("play_1", "Processing playlist..."))
    try:
        await _enqueue_and_play(client, chat_id, user_id, user_name, list(_playlist), video, mystic)
    except Exception as e:
        return await mystic.edit_text(f"Error: {e}")
    return await mystic.delete()


@app.on_message(
    filters.command(["playplaylist", "vplayplaylist"]) & BL_FILTER & filters.group
)
async def play_playlist_command(client, message):
    _ = _get_strings(message)
    mode = message.command[0][0]
    user_id = message.from_user.id
    _playlist = await get_playlist_names(user_id)
    if not _playlist:
        try:
            return await message.reply(_.get("playlist_3", "Playlist is empty."), quote=True)
        except Exception:
            return

    chat_id = message.chat.id
    user_name = message.from_user.first_name

    try:
        await message.delete()
    except Exception:
        pass

    video = True if mode == "v" else False
    mystic = await message.reply_text(_.get("play_1", "Processing playlist..."))
    try:
        await _enqueue_and_play(client, chat_id, user_id, user_name, list(_playlist), video, mystic)
    except Exception as e:
        return await mystic.edit_text(f"Error: {e}")

    return await mystic.delete()


# Combined add_playlist function
@app.on_message(filters.command(ADDPLAYLIST_COMMAND) & BL_FILTER)
async def add_playlist(client, message: Message):
    _ = _get_strings(message)
    if len(message.command) < 2:
        return await message.reply_text(
            "**➻ ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴍᴇ ᴀ sᴏɴɢ ɴᴀᴍᴇ ᴏʀ sᴏɴɢ ʟɪɴᴋ ᴏʀ ʏᴏᴜᴛᴜʙᴇ ᴘʟᴀʏʟɪsᴛ ʟɪɴᴋ ᴀғᴛᴇʀ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ..**\n\n**➥ ᴇxᴀᴍᴘʟᴇs:**\n\n▷ `/addplaylist Blue Eyes` (ᴘᴜᴛ ᴀ sᴘᴇᴄɪғɪᴄ sᴏɴɢ ɴᴀᴍᴇ)\n\n▷ /addplaylist [ʏᴏᴜᴛᴜʙᴇ ᴘʟᴀʏʟɪsᴛ ʟɪɴᴋ] (ᴛᴏ ᴀᴅᴅ ᴀʟʟ sᴏɴɢs ғʀᴏᴍ ᴀ ʏᴏᴜᴛᴜʙᴇ ᴘʟᴀʏʟɪsᴛ ɪɴ ʙᴏᴛ ᴘʟᴀʏʟɪsᴛ.)"
        )

    query = message.command[1]

    # Check if the provided input is a YouTube playlist link
    if "youtube.com/playlist" in query:
        adding = await message.reply_text(
            "**🎧 ᴀᴅᴅɪɴɢ sᴏɴɢs ɪɴ ᴘʟᴀʏʟɪsᴛ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..**"
        )
        try:
            from pytube import Playlist, YouTube as PyTubeVideo

            playlist_obj = Playlist(query)
            video_urls = playlist_obj.video_urls
        except Exception as e:
            return await message.reply_text(f"Error: {e}")

        if not video_urls:
            return await message.reply_text(
                "**➻ ɴᴏ sᴏɴɢs ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ ᴘʟᴀʏʟɪsᴛ ʟɪɴᴋs.\n\n**➥ ᴛʀʏ ᴏᴛʜᴇʀ ᴘʟᴀʏʟɪsᴛ ʟɪɴᴋ**"
            )

        user_id = message.from_user.id
        for video_url in video_urls:
            video_id = video_url.split("v=")[-1]
            try:
                pyt = PyTubeVideo(video_url)
                title = pyt.title
                duration = pyt.length
            except Exception as e:
                return await message.reply_text(f"ᴇʀʀᴏʀ ғᴇᴛᴄʜɪɴɢ ᴠɪᴅᴇᴏ ɪɴғᴏ: {e}")

            plist = {
                "videoid": video_id,
                "title": title,
                "duration": duration,
            }
            await save_playlist(user_id, video_id, plist)

        keyboardes = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "๏ ᴡᴀɴᴛ ʀᴇᴍᴏᴠᴇ ᴀɴʏ sᴏɴɢs? ๏",
                        callback_data=f"open_playlist {user_id}",
                    )
                ]
            ]
        )
        await adding.delete()
        return await message.reply_text(
            text="**➻ ᴀʟʟ sᴏɴɢs ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ғʀᴏᴍ ʏᴏᴜʀ ʏᴏᴜᴛᴜʙᴇ ᴘʟᴀʏʟɪsᴛ ʟɪɴᴋ✅**\n\n**➥ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀɴʏ sᴏɴɢ ᴛʜᴇɴ ᴄʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ.\n\n**▷ ᴄʜᴇᴄᴋ ʙʏ » /playlist**\n\n▷ **ᴘʟᴀʏ ʙʏ » /play**",
            reply_markup=keyboardes,
        )

    if "youtube.com/@" in query:
        addin = await message.reply_text(
            "**🎧 ᴀᴅᴅɪɴɢ sᴏɴɢs ɪɴ ᴘʟᴀʏʟɪsᴛ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..**"
        )
        try:
            from pytube import YouTube as PyTubeVideo

            videos = YouTube_videos(f"{query}/videos")
            video_urls = [video["url"] for video in videos]
        except Exception as e:
            return await message.reply_text(f"Error: {e}")

        if not video_urls:
            return await message.reply_text(
                "**➻ ɴᴏ sᴏɴɢs ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ YouTube channel.\n\n**➥ ᴛʀʏ ᴏᴛʜᴇʀ YouTube channel ʟɪɴᴋ**"
            )

        user_id = message.from_user.id
        videosid = query.split("/")[-1].split("?")[0]
        for _ in video_urls:
            try:
                pyt = PyTubeVideo(f"https://youtu.be/{videosid}")
                title = pyt.title
                duration = pyt.length
            except Exception as e:
                return await message.reply_text(f"ᴇʀʀᴏʀ ғᴇᴛᴄʜɪɴɢ ᴠɪᴅᴇᴏ ɪɴғᴏ: {e}")

            plist = {
                "videoid": videosid,
                "title": title,
                "duration": duration,
            }
            await save_playlist(user_id, videosid, plist)

        keyboardes = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "๏ ᴡᴀɴᴛ ʀᴇᴍᴏᴠᴇ ᴀɴʏ sᴏɴɢs? ๏",
                        callback_data=f"open_playlist {user_id}",
                    )
                ]
            ]
        )
        await addin.delete()
        return await message.reply_text(
            text="**➻ ᴀʟʟ sᴏɴɢs ʜᴀs ʙᴇᴇɴ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ғʀᴏᴍ ʏᴏᴜʀ ʏᴏᴜᴛᴜʙᴇ channel ʟɪɴᴋ✅**\n\n**➥ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀɴʏ sᴏɴɢ ᴛʜᴇɴ ᴄʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ.\n\n**▷ ᴄʜᴇᴄᴋ ʙʏ » /playlist**\n\n▷ **ᴘʟᴀʏ ʙʏ » /play**",
            reply_markup=keyboardes,
        )

    # Check if the provided input is a YouTube video link
    if "https://youtu.be" in query:
        try:
            add = await message.reply_text(
                "**🎧 ᴀᴅᴅɪɴɢ sᴏɴɢs ɪɴ ᴘʟᴀʏʟɪsᴛ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ..**"
            )
            from pytube import YouTube as PyTubeVideo

            videoid = query.split("/")[-1].split("?")[0]
            user_id = message.from_user.id
            thumbnail = f"https://img.youtube.com/vi/{videoid}/maxresdefault.jpg"
            _check = await get_playlist(user_id, videoid)
            if _check:
                try:
                    await add.delete()
                    return await message.reply_photo(
                        thumbnail, caption=_.get("playlist_8", "Already in playlist.")
                    )
                except KeyError:
                    pass

            _count = await get_playlist_names(user_id)
            count = len(_count)
            if count >= SERVER_PLAYLIST_LIMIT:
                try:
                    return await message.reply_text(
                        _.get("playlist_9", "Playlist limit reached: {}").format(
                            SERVER_PLAYLIST_LIMIT
                        )
                    )
                except KeyError:
                    pass

            try:
                pyt = PyTubeVideo(f"https://youtu.be/{videoid}")
                title = pyt.title
                duration = pyt.length
                plist = {
                    "videoid": videoid,
                    "title": title,
                    "duration": duration,
                }
                await save_playlist(user_id, videoid, plist)

                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "๏ Remove from Playlist ๏",
                                callback_data=f"remove_playlist {videoid}",
                            )
                        ]
                    ]
                )
                await add.delete()
                await message.reply_photo(
                    thumbnail,
                    caption="**➻ ᴀᴅᴅᴇᴅ sᴏɴɢ ɪɴ ʏᴏᴜʀ ʙᴏᴛ ᴘʟᴀʏʟɪsᴛ✅**\n\n**➥ ᴄʜᴇᴄᴋ ʙʏ » /playlist**\n\n**➥ ᴅᴇʟᴇᴛᴇ ʙʏ » /delplaylist**\n\n**➥ ᴀɴᴅ ᴘʟᴀʏ ʙʏ » /play (ɢʀᴏᴜᴘs ᴏɴʟʏ)**",
                    reply_markup=keyboard,
                )
            except Exception as e:
                print(f"Error: {e}")
                await message.reply_text(str(e))
        except Exception as e:
            return await message.reply_text(str(e))
    else:
        # Add a specific song by name
        query = " ".join(message.command[1:])
        print(query)

        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            thumbnail = results[0]["thumbnails"][0]
            videoid = results[0]["id"]
            user_id = message.from_user.id

            _check = await get_playlist(user_id, videoid)
            if _check:
                try:
                    return await message.reply_photo(
                        thumbnail, caption=_.get("playlist_8", "Already in playlist.")
                    )
                except KeyError:
                    pass

            _count = await get_playlist_names(user_id)
            count = len(_count)
            if count >= SERVER_PLAYLIST_LIMIT:
                try:
                    return await message.reply_text(
                        _.get("playlist_9", "Playlist limit reached: {}").format(
                            SERVER_PLAYLIST_LIMIT
                        )
                    )
                except KeyError:
                    pass

            m = await message.reply("**🔄 ᴀᴅᴅɪɴɢ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ... **")
            if hasattr(yt, "details"):
                title, duration_min, _, _, _ = await yt.details(videoid, True)
            else:
                title = results[0].get("title", videoid)
                duration_min = results[0].get("duration", "0:00")
            title = (str(title)[:50]).title()
            plist = {
                "videoid": videoid,
                "title": title,
                "duration": duration_min,
            }
            await save_playlist(user_id, videoid, plist)

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "๏ Remove from Playlist ๏",
                            callback_data=f"remove_playlist {videoid}",
                        )
                    ]
                ]
            )
            await m.delete()
            await message.reply_photo(
                thumbnail,
                caption="**➻ ᴀᴅᴅᴇᴅ sᴏɴɢ ɪɴ ʏᴏᴜʀ ʙᴏᴛ ᴘʟᴀʏʟɪsᴛ✅**\n\n**➥ ᴄʜᴇᴄᴋ ʙʏ » /playlist**\n\n**➥ ᴅᴇʟᴇᴛᴇ ʙʏ » /delplaylist**\n\n**➥ ᴀɴᴅ ᴘʟᴀʏ ʙʏ » /play (ɢʀᴏᴜᴘs ᴏɴʟʏ)**",
                reply_markup=keyboard,
            )

        except KeyError:
            return await message.reply_text("ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ ғᴏʀᴍᴀᴛ ʀᴇᴄᴇɪᴠᴇᴅ.")
        except Exception:
            pass


@app.on_callback_query(filters.regex("open_playlist") & BL_FILTER)
async def open_playlist(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    _playlist = await get_playlist_names(CallbackQuery.from_user.id)
    if _playlist:
        get = await CallbackQuery.message.edit_text(_.get("playlist_2", "Loading..."))
    else:
        return await CallbackQuery.message.edit_text(_.get("playlist_3", "Playlist is empty."))
    keyboard, count = await get_keyboard(_, CallbackQuery.from_user.id)
    await get.edit_text(
        _.get("playlist_7", "Total songs: {}").format(count), reply_markup=keyboard
    )


@app.on_callback_query(filters.regex("remove_playlist") & BL_FILTER)
async def del_plist(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    callback_data = CallbackQuery.data.strip()
    videoid = callback_data.split(None, 1)[1]
    deleted = await delete_playlist(CallbackQuery.from_user.id, videoid)
    if deleted:
        try:
            await CallbackQuery.answer(
                _.get("playlist_11", "Removed from playlist."), show_alert=True
            )
        except Exception:
            pass
    else:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_12", "Not found in playlist."), show_alert=True
            )
        except Exception:
            return
    keyboards = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "๏ ʀᴇᴄᴏᴠᴇʀ ʏᴏᴜʀ sᴏɴɢ ๏", callback_data=f"recover_playlist {videoid}"
                )
            ]
        ]
    )
    return await CallbackQuery.edit_message_text(
        text="**➻ ʏᴏᴜʀ sᴏɴɢ ʜᴀs ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ʏᴏᴜʀ ʙᴏᴛ ᴘʟᴀʏʟɪsᴛ**\n\n**➥ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀᴇᴄᴏᴠᴇʀ ʏᴏᴜʀ sᴏɴɢ ɪɴ ʏᴏᴜʀ ᴘʟᴀʏʟɪsᴛ ᴛʜᴇɴ ᴄʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ**",
        reply_markup=keyboards,
    )


@app.on_callback_query(filters.regex("recover_playlist") & BL_FILTER)
async def recover_playlist_cb(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    callback_data = CallbackQuery.data.strip()
    videoid = callback_data.split(None, 1)[1]
    user_id = CallbackQuery.from_user.id
    _check = await get_playlist(user_id, videoid)
    if _check:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_8", "Already in playlist."), show_alert=True
            )
        except Exception:
            return
    _count = await get_playlist_names(user_id)
    count = len(_count)
    if count >= SERVER_PLAYLIST_LIMIT:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_9", "Playlist limit reached: {}").format(
                    SERVER_PLAYLIST_LIMIT
                ),
                show_alert=True,
            )
        except Exception:
            return
    if hasattr(yt, "details"):
        title, duration_min, _, _, vidid = await yt.details(videoid, True)
    else:
        title, duration_min, vidid = str(videoid), "0:00", str(videoid)
    title = (str(title)[:50]).title()
    plist = {
        "videoid": vidid,
        "title": title,
        "duration": duration_min,
    }
    await save_playlist(user_id, videoid, plist)
    try:
        keyboardss = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "๏ ʀᴇᴍᴏᴠᴇ ᴀɢᴀɪɴ ๏", callback_data=f"remove_playlist {videoid}"
                    )
                ]
            ]
        )
        return await CallbackQuery.edit_message_text(
            text="**➻ ʀᴇᴄᴏᴠᴇʀᴇᴅ sᴏɴɢ ɪɴ ʏᴏᴜʀ ᴘʟᴀʏʟɪsᴛ**\n\n**➥ Cʜᴇᴄᴋ Pʟᴀʏʟɪsᴛ ʙʏ /playlist**\n\n**➥ ᴅᴇʟᴇᴛᴇ ᴘʟᴀʏʟɪsᴛ ʙʏ » /delplaylist**\n\n**➥ ᴀɴᴅ ᴘʟᴀʏ ᴘʟᴀʏʟɪsᴛ ʙʏ » /play**",
            reply_markup=keyboardss,
        )
    except Exception:
        return


@app.on_callback_query(filters.regex("add_playlist") & BL_FILTER)
async def add_playlist_info(client, CallbackQuery):
    await CallbackQuery.answer(
        "➻ ᴛᴏ ᴀᴅᴅ ᴀ sᴏɴɢ ɪɴ ʏᴏᴜʀ ᴘʟᴀʏʟɪsᴛ ᴊᴜsᴛ ᴛʏᴘᴇ /addplaylist (Here your song name)\n\n➥ ᴇxᴀᴍᴘʟᴇ » /addplaylist Blue Eyes Blue tyes.",
        show_alert=True,
    )


@app.on_callback_query(filters.regex("branded_playlist") & BL_FILTER)
async def add_branded_playlist(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    callback_data = CallbackQuery.data.strip()
    videoid = callback_data.split(None, 1)[1]
    user_id = CallbackQuery.from_user.id
    _check = await get_playlist(user_id, videoid)
    if _check:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_8", "Already in playlist."), show_alert=True
            )
        except Exception:
            return
    _count = await get_playlist_names(user_id)
    count = len(_count)
    if count >= SERVER_PLAYLIST_LIMIT:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_9", "Playlist limit reached: {}").format(
                    SERVER_PLAYLIST_LIMIT
                ),
                show_alert=True,
            )
        except Exception:
            return
    if hasattr(yt, "details"):
        title, duration_min, _, _, vidid = await yt.details(videoid, True)
    else:
        title, duration_min, vidid = str(videoid), "0:00", str(videoid)
    title = (str(title)[:50]).title()
    plist = {
        "videoid": vidid,
        "title": title,
        "duration": duration_min,
    }
    await save_playlist(user_id, videoid, plist)
    try:
        short_title = (title[:30]).title()
        return await CallbackQuery.answer(
            _.get("playlist_10", "Added: {}").format(short_title), show_alert=True
        )
    except Exception:
        return


@app.on_message(filters.command(DELETE_ALL_PLAYLIST_COMMAND) & BL_FILTER)
async def delete_all_playlists(client, message):
    _ = _get_strings(message)
    user_id = message.from_user.id
    _playlist = await get_playlist_names(user_id)
    if _playlist:
        try:
            upl = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=_.get("PL_B_5", "Yes, Delete All"),
                            callback_data="delete_whole_playlist",
                        ),
                        InlineKeyboardButton(
                            text=_.get("CLOSE_BUTTON", "Cancel"),
                            callback_data="close",
                        ),
                    ]
                ]
            )
            await message.reply_text(
                _.get("playlist_14", "Are you sure you want to delete all songs?"),
                reply_markup=upl,
            )
        except Exception:
            pass
    else:
        await message.reply_text(_.get("playlist_3", "Playlist is empty."))


@app.on_callback_query(filters.regex("del_playlist") & BL_FILTER)
async def del_plist_cb(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    callback_data = CallbackQuery.data.strip()
    videoid = callback_data.split(None, 1)[1]
    user_id = CallbackQuery.from_user.id
    deleted = await delete_playlist(CallbackQuery.from_user.id, videoid)
    if deleted:
        try:
            await CallbackQuery.answer(
                _.get("playlist_11", "Removed from playlist."), show_alert=True
            )
        except Exception:
            pass
    else:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_12", "Not found in playlist."), show_alert=True
            )
        except Exception:
            return
    keyboard, _ = await get_keyboard(_, user_id)
    return await CallbackQuery.edit_message_reply_markup(reply_markup=keyboard)


@app.on_callback_query(filters.regex("delete_whole_playlist") & BL_FILTER)
async def del_whole_playlist(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    _playlist = await get_playlist_names(CallbackQuery.from_user.id)
    for x in _playlist:
        await CallbackQuery.answer(
            "➻ ᴏᴋ sɪʀ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ.\n\n➥ ᴅᴇʟᴇᴛɪɴɢ ʏᴏᴜʀ ᴘʟᴀʏʟɪsᴛ...", show_alert=True
        )
        await delete_playlist(CallbackQuery.from_user.id, x)
    return await CallbackQuery.edit_message_text(
        _.get("playlist_13", "Playlist deleted.")
    )


@app.on_callback_query(filters.regex("get_playlist_playmode") & BL_FILTER)
async def get_playlist_playmode_(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Audio", callback_data="play_playlist a"
                ),
                InlineKeyboardButton(
                    text="Video", callback_data="play_playlist v"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_.get("CLOSE_BUTTON", "Close"), callback_data="close"
                )
            ],
        ]
    )
    return await CallbackQuery.edit_message_reply_markup(reply_markup=buttons)


@app.on_callback_query(filters.regex("delete_warning") & BL_FILTER)
async def delete_warning_message(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_.get("PL_B_5", "Yes, Delete All"),
                    callback_data="delete_whole_playlist",
                ),
                InlineKeyboardButton(
                    text=_.get("CLOSE_BUTTON", "Cancel"),
                    callback_data="close",
                ),
            ]
        ]
    )
    return await CallbackQuery.edit_message_text(
        _.get("playlist_14", "Are you sure you want to delete all songs?"),
        reply_markup=upl,
    )


@app.on_callback_query(filters.regex("home_play") & BL_FILTER)
async def home_play_(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Audio", callback_data="play_playlist a"
                ),
                InlineKeyboardButton(
                    text="Video", callback_data="play_playlist v"
                ),
            ]
        ]
    )
    return await CallbackQuery.edit_message_reply_markup(reply_markup=buttons)


@app.on_callback_query(filters.regex("del_back_playlist") & BL_FILTER)
async def del_back_playlist(client, CallbackQuery):
    _ = _get_strings(CallbackQuery)
    user_id = CallbackQuery.from_user.id
    _playlist = await get_playlist_names(user_id)
    if _playlist:
        try:
            await CallbackQuery.answer(_.get("playlist_2", "Loading..."), show_alert=True)
        except Exception:
            pass
    else:
        try:
            return await CallbackQuery.answer(
                _.get("playlist_3", "Playlist is empty."), show_alert=True
            )
        except Exception:
            return
    keyboard, count = await get_keyboard(_, user_id)
    return await CallbackQuery.edit_message_text(
        _.get("playlist_7", "Total songs: {}").format(count), reply_markup=keyboard
    )
