import asyncio
import random
from pyrogram import Client

# Replace these with your session strings for each bot
SESSION_STRINGS = [
    "PASTE_STRING1",
    "PASTE_STRING2",
    "PASTE_STRING3",
]

async def start_bot(session_str: str):
    """
    Start a single Pyrogram bot safely with a unique session name
    """
    # unique session name prevents SQLite locks
    session_name = f"bot_{random.randint(1000,9999)}"
    bot = Client(session_name=session_name, session_string=session_str)

    try:
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Bot @{me.username} started with session {session_name}")
    except Exception as e:
        print(f"❌ Failed to start bot with session {session_name}: {e}")
        return None

    return bot

async def main():
    bots = []
    for s in SESSION_STRINGS:
        bot = await start_bot(s)
        if bot:
            bots.append(bot)
        # small delay to avoid SQLite lock
        await asyncio.sleep(0.5)

    print(f"Total bots running: {len(bots)}")

    # Keep bots running
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
