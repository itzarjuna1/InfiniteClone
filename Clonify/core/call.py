import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup

from pytgcalls import PyTgCalls
from pytgcalls.exceptions import GroupCallAlreadyExists, GroupCallNotFound
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo
from pytgcalls.types.stream import StreamAudioEnded

import config
from Clonify import LOGGER, YouTube, app
from Clonify.misc import db
from Clonify.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from Clonify.utils.exceptions import AssistantErr
from Clonify.utils.formatters import check_duration, seconds_to_min, speed_converter
from Clonify.utils.inline.play import stream_markup, telegram_markup
from Clonify.utils.stream.autoclear import auto_clean
from strings import get_string
from Clonify.utils.thumbnails import get_thumb

autoend = {}
counter = {}


async def _clear_(chat_id: int):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call:
    def __init__(self):
        self.userbot = Client(
            name="ClonifyAssistant",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        self.pytgcalls = PyTgCalls(self.userbot, cache_duration=150)

    # ========== BASIC CONTROLS ==========

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause_stream(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume_stream(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def force_stop_stream(self, chat_id: int):
        try:
            await self.pytgcalls.leave_group_call(chat_id)
        except:
            pass
        await _clear_(chat_id)

    # ========== JOIN / STREAM ==========

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link: str,
        video: bool = False,
    ):
        assistant = await group_assistant(self, chat_id)
        _ = get_string(await get_lang(chat_id))

        stream = (
            AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
            if video
            else AudioPiped(link, audio_parameters=HighQualityAudio())
        )

        try:
            await assistant.join_group_call(chat_id, stream)
        except GroupCallAlreadyExists:
            raise AssistantErr(_["call_9"])
        except GroupCallNotFound:
            raise AssistantErr(_["call_8"])

        await add_active_chat(chat_id)
        await music_on(chat_id)

        if video:
            await add_active_video_chat(chat_id)

        if await is_autoend():
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def skip_stream(self, chat_id: int, link: str, video: bool = False):
        assistant = await group_assistant(self, chat_id)
        stream = (
            AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
            if video
            else AudioPiped(link, audio_parameters=HighQualityAudio())
        )
        await assistant.change_stream(chat_id, stream)

    # ========== CHANGE / QUEUE ==========

    async def change_stream(self, client, chat_id: int):
        queue = db.get(chat_id)
        if not queue:
            await self.stop_stream(chat_id)
            return

        loop = await get_loop(chat_id)
        if loop == 0:
            played = queue.pop(0)
        else:
            await set_loop(chat_id, loop - 1)
            played = queue[0]

        await auto_clean(played)

        if not queue:
            await self.stop_stream(chat_id)
            return

        next_song = queue[0]
        file = next_song["file"]
        streamtype = next_song["streamtype"]

        stream = (
            AudioVideoPiped(
                file,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
            if streamtype == "video"
            else AudioPiped(file, audio_parameters=HighQualityAudio())
        )

        await client.change_stream(chat_id, stream)

    # ========== EVENTS ==========

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Assistant...")
        await self.userbot.start()
        await self.pytgcalls.start()

    async def decorators(self):
        @self.pytgcalls.on_stream_end()
        async def stream_end_handler(client, update: Update):
            if not isinstance(update, StreamAudioEnded):
                return
            await self.change_stream(client, update.chat_id)


PRO = Call()
