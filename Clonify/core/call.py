import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup

from pytgcalls import PyTgCalls
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    NotInGroupCall,
)
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import (
    HighQualityAudio,
    MediumQualityVideo,
)
from pytgcalls.types.stream import StreamAudioEnded

from ntgcalls import StreamType

import config
from Clonify import LOGGER, app, YouTube
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
from Clonify.utils.formatters import (
    check_duration,
    seconds_to_min,
    speed_converter,
)
from Clonify.utils.inline.play import stream_markup, telegram_markup
from Clonify.utils.stream.autoclear import auto_clean
from Clonify.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}


async def _clear_(chat_id: int):
    db[chat_id] = []
    await remove_active_chat(chat_id)
    await remove_active_video_chat(chat_id)


class Call:
    def __init__(self):
        self.userbot1 = Client(
            "ClonifyAssistant1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )

        self.one = PyTgCalls(self.userbot1, cache_duration=150)

    # ───────────── BASIC CONTROLS ───────────── #

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
        except (NoActiveGroupCall, NotInGroupCall):
            pass

    async def force_stop_stream(self, chat_id: int):
        try:
            await self.one.leave_group_call(chat_id)
        except (NoActiveGroupCall, NotInGroupCall):
            pass
        await _clear_(chat_id)

    # ───────────── JOIN CALL ───────────── #

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link: str,
        video: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = get_string(language)

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
            await assistant.join_group_call(
                chat_id,
                stream,
                stream_type=StreamType().pulse_stream,
            )
        except AlreadyJoinedError:
            raise AssistantErr(_["call_9"])
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])

        await add_active_chat(chat_id)
        await music_on(chat_id)

        if video:
            await add_active_video_chat(chat_id)

        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    # ───────────── STREAM CHANGE ───────────── #

    async def change_stream(self, client, chat_id: int):
        queue = db.get(chat_id)
        if not queue:
            return

        loop = await get_loop(chat_id)

        try:
            if loop == 0:
                popped = queue.pop(0)
                await auto_clean(popped)
            else:
                await set_loop(chat_id, loop - 1)

            if not queue:
                await _clear_(chat_id)
                return await client.leave_group_call(chat_id)

        except Exception:
            await _clear_(chat_id)
            return

        data = queue[0]
        file = data["file"]
        streamtype = data["streamtype"]

        stream = (
            AudioVideoPiped(
                file,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
            if streamtype == "video"
            else AudioPiped(file, audio_parameters=HighQualityAudio())
        )

        try:
            await client.change_stream(chat_id, stream)
        except Exception:
            await _clear_(chat_id)
            return

    # ───────────── EVENTS ───────────── #

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client")
        await self.one.start()

    async def decorators(self):
        @self.one.on_stream_end()
        async def stream_end(_, update: Update):
            if isinstance(update, StreamAudioEnded):
                await self.change_stream(_, update.chat_id)

        @self.one.on_left()
        @self.one.on_kicked()
        @self.one.on_closed_voice_chat()
        async def leave_handler(_, chat_id: int):
            await self.stop_stream(chat_id)


PRO = Call()
