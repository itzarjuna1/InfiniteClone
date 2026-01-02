import asyncio
from pyrogram import Client

# Your string sessions (bot OR user)
SESSION_STRINGS = [
    "PASTE_STRING1",
    "PASTE_STRING2",
    "PASTE_STRING3",
]

async def start_bot(session_str: str):
    """
    Start a Pyrogram client using STRING SESSION ONLY (no SQLite)
    """
    bot = Client(
        name=None,                 # 🔴 IMPORTANT
        session_string=session_str,
        api_id=API_ID,
        api_hash=API_HASH
    )

    try:
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Bot @{me.username} started")
        return bot
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        return None

async def main():
    bots = []

    for s in SESSION_STRINGS:
        bot = await start_bot(s)
        if bot:
            bots.append(bot)
        await asyncio.sleep(1)  # small delay (safe)

    print(f"🚀 Total bots running: {len(bots)}")

    # Keep process alive
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
