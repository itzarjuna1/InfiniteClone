import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    TelegramServerError,
)
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
from Clonify.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}


async def clear_chat(chat_id: int):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


class Call:
    def __init__(self):
        self.userbot = Client(
            name="RAUSHANAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING_SESSION),
        )
        self.call = PyTgCalls(self.userbot, cache_duration=150)

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause_stream(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume_stream(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await clear_chat(chat_id)
            await assistant.leave_group_call(chat_id)
        except Exception:
            pass

    async def force_stop_stream(self, chat_id: int):
        try:
            await self.call.leave_group_call(chat_id)
        except Exception:
            pass
        await clear_chat(chat_id)

    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: bool = False,
    ):
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

    async def seek_stream(
        self,
        chat_id: int,
        file_path: str,
        to_seek: int,
        duration: int,
        mode: str,
    ):
        assistant = await group_assistant(self, chat_id)
        stream = (
            AudioVideoPiped(
                file_path,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
            )
            if mode == "video"
            else AudioPiped(
                file_path,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
            )
        )
        await assistant.change_stream(chat_id, stream)

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link: str,
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
                stream_type=StreamType().pulse_stream,
            )
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except AlreadyJoinedError:
            raise AssistantErr(_["call_9"])
        except TelegramServerError:
            raise AssistantErr(_["call_10"])

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)

        if await is_autoend():
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def change_stream(self, client, chat_id: int):
        queue = db.get(chat_id)
        if not queue:
            await clear_chat(chat_id)
            return await client.leave_group_call(chat_id)

        loop = await get_loop(chat_id)
        if loop == 0:
            old = queue.pop(0)
            await auto_clean(old)
        else:
            await set_loop(chat_id, loop - 1)

        if not queue:
            await clear_chat(chat_id)
            return await client.leave_group_call(chat_id)

        next_track = queue[0]
        stream = (
            AudioVideoPiped(
                next_track["file"],
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
            if next_track["streamtype"] == "video"
            else AudioPiped(
                next_track["file"],
                audio_parameters=HighQualityAudio(),
            )
        )
        await client.change_stream(chat_id, stream)

    async def ping(self):
        return str(round(await self.call.ping(), 3))

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client...")
        await self.call.start()

    async def decorators(self):
        @self.call.on_kicked()
        @self.call.on_closed_voice_chat()
        @self.call.on_left()
        async def vc_closed(_, chat_id: int):
            await self.stop_stream(chat_id)

        @self.call.on_stream_end()
        async def stream_end(client, update: Update):
            if isinstance(update, StreamAudioEnded):
                await self.change_stream(client, update.chat_id)


PRO = Call()
