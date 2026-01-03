import asyncio
import logging
import uuid
import requests
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.errors import AccessTokenExpired, AccessTokenInvalid

from Clonify import app
from Clonify.misc import SUDOERS
from Clonify.utils.decorators.language import language
from Clonify.utils.database.clonedb import (
    clonebotdb,
    has_user_cloned_any_bot,
    get_owner_id_from_db,
)

from config import (
    API_ID,
    API_HASH,
    OWNER_ID,
    SUPPORT_CHAT,
    CLONE_LOGGER,
)

log = logging.getLogger(__name__)

CLONES = set()

# ===================== CONSTANTS ===================== #

C_BOT_DESC = (
    "Wᴀɴᴛ ᴀ ʙᴏᴛ ʟɪᴋᴇ ᴛʜɪs? Cʟᴏɴᴇ ɪᴛ ɴᴏᴡ! ✅\n\n"
    "Vɪsɪᴛ: @HinduMusicRobot\n"
    "Sᴜᴘᴘᴏʀᴛ: @GOJO_NOBITA_II"
)

C_BOT_COMMANDS = [
    {"command": "start", "description": "Start the bot"},
    {"command": "help", "description": "Help menu"},
    {"command": "play", "description": "Play music"},
    {"command": "pause", "description": "Pause stream"},
    {"command": "resume", "description": "Resume stream"},
    {"command": "skip", "description": "Skip track"},
    {"command": "end", "description": "End stream"},
    {"command": "ping", "description": "Ping bot"},
    {"command": "id", "description": "Get ID"},
]

# ===================== SAFE CLIENT ===================== #

def build_clone_client(bot_id: int, bot_token: str) -> Client:
    return Client(
        name=f"clone_{bot_id}_{uuid.uuid4().hex[:6]}",  # ✅ NEVER None
        api_id=int(API_ID),
        api_hash=str(API_HASH),
        bot_token=str(bot_token),
        plugins=dict(root="Clonify.cplugin"),
        in_memory=True,  # ✅ no sqlite file
    )

# ===================== CLONE COMMAND ===================== #

@app.on_message(filters.command("clone"))
@language
async def clone_bot(_, message, _t):
    user_id = message.from_user.id

    if await has_user_cloned_any_bot(user_id) and user_id != OWNER_ID:
        return await message.reply_text(_t["C_B_H_0"])

    if len(message.command) < 2:
        return await message.reply_text(_t["C_B_H_1"])

    bot_token = message.command[1].strip()
    msg = await message.reply_text(_t["C_B_H_2"])

    try:
        temp = build_clone_client(0, bot_token)
        await temp.start()
        bot = await temp.get_me()

    except (AccessTokenExpired, AccessTokenInvalid):
        return await msg.edit_text(_t["C_B_H_3"])
    except Exception as e:
        return await msg.edit_text(f"❌ Error: `{e}`")

    clonebotdb.insert_one(
        {
            "bot_id": bot.id,
            "user_id": user_id,
            "name": bot.first_name,
            "username": bot.username,
            "token": bot_token,
            "premium": False,
            "date": datetime.utcnow(),
        }
    )

    CLONES.add(bot.id)

    requests.post(
        f"https://api.telegram.org/bot{bot_token}/setMyCommands",
        json={"commands": C_BOT_COMMANDS},
    )

    requests.post(
        f"https://api.telegram.org/bot{bot_token}/setMyDescription",
        data={"description": C_BOT_DESC},
    )

    await app.send_message(
        CLONE_LOGGER,
        f"🤖 **New Clone**\n\n"
        f"Bot: @{bot.username}\n"
        f"Owner: [{message.from_user.first_name}](tg://user?id={user_id})",
    )

    await msg.edit_text(_t["C_B_H_6"].format(bot.username))

# ===================== DELETE CLONE ===================== #

@app.on_message(filters.command(["delclone", "delbot", "rmbot"]))
@language
async def delete_clone(_, message, _t):
    if len(message.command) < 2:
        return await message.reply_text(_t["C_B_H_8"])

    query = message.command[1].lstrip("@")
    bot = clonebotdb.find_one(
        {"$or": [{"username": query}, {"token": query}]}
    )

    if not bot:
        return await message.reply_text(_t["C_B_H_11"])

    owner = get_owner_id_from_db(bot["bot_id"])
    if message.from_user.id not in [OWNER_ID, owner]:
        return await message.reply_text(_t["NOT_C_OWNER"].format(SUPPORT_CHAT))

    clonebotdb.delete_one({"_id": bot["_id"]})
    CLONES.discard(bot["bot_id"])

    await message.reply_text(_t["C_B_H_10"])

# ===================== SAFE RESTART ===================== #

async def restart_bots():
    log.info("Starting cloned bots safely...")

    for bot in clonebotdb.find():
        try:
            client = build_clone_client(bot["bot_id"], bot["token"])
            await client.start()
            me = await client.get_me()
            CLONES.add(me.id)
            await asyncio.sleep(1)

        except Exception as e:
            log.error(f"Skipped clone restart: {e}")

    await app.send_message(CLONE_LOGGER, "✅ All cloned bots started safely.")

# ===================== LIST USER CLONES ===================== #

@app.on_message(filters.command(["mybots", "mybot"]))
@language
async def my_bots(_, message, _t):
    bots = list(clonebotdb.find({"user_id": message.from_user.id}))

    if not bots:
        return await message.reply_text(_t["C_B_H_16"])

    text = f"**Your Cloned Bots ({len(bots)}):**\n\n"
    for b in bots:
        text += f"• @{b['username']}\n"

    await message.reply_text(text)

# ===================== ADMIN LIST ===================== #

@app.on_message(filters.command("cloned") & SUDOERS)
@language
async def list_all_clones(_, message, _t):
    bots = list(clonebotdb.find())

    text = f"**Total Clones:** `{len(bots)}`\n\n"
    for b in bots:
        text += f"• @{b['username']} (`{b['bot_id']}`)\n"

    await message.reply_text(text)
