import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup

from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types import Update
from pytgcalls.types.stream import StreamEnded
from pytgcalls.types.stream import StreamEnded
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.stream.quality import HighQualityAudio, MediumQualityVideo
from ntgcalls import StreamType

from pytgcalls.exceptions import (
    AlreadyInVoiceChat,
    GroupCallNotFound,
    NotInVoiceChat,
    RPCError,
)
from Clonify.utils.exceptions import AssistantErr
from Clonify.utils.formatters import check_duration, seconds_to_min, speed_converter
from Clonify.utils.inline.play import stream_markup
from Clonify.utils.stream.autoclear import auto_clean
from Clonify.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}

async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call:
    def __init__(self):
        self.userbot1 = Client(
            name="RAUSHANAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )

        self.one = PyTgCalls(self.userbot1, cache_duration=150)

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_group_call(chat_id)
        except Exception:
            pass

    async def skip_stream(self, chat_id: int, link: str, video=False):
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

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link,
        video: bool = False,
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
                stream_type=StreamType.PULSE_STREAM,
            )
        except Exception:
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

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        loop = await get_loop(chat_id)

        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                await set_loop(chat_id, loop - 1)
                popped = None

            await auto_clean(popped)

            if not check:
                await _clear_(chat_id)
                return await client.leave_group_call(chat_id)
        except Exception:
            await _clear_(chat_id)
            return await client.leave_group_call(chat_id)

        next_file = check[0]["file"]
        video = check[0]["streamtype"] == "video"

        stream = (
            AudioVideoPiped(
                next_file,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
            if video
            else AudioPiped(next_file, audio_parameters=HighQualityAudio())
        )

        await client.change_stream(chat_id, stream)

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls 2.2.6 Client...")
        await self.userbot1.start()
        await self.one.start()

    async def decorators(self):
        @self.one.on_stream_end()
        async def stream_end_handler(client, update: Update):
            if not isinstance(update, StreamEnded):
                return
            await self.change_stream(client, update.chat_id)


PRO = Call()
