import asyncio
from bot import create_bot
from bot.core.config import get_settings

async def main():
    bot = create_bot()
    async with bot:
        await bot.start(get_settings().discord_token)

if __name__ == "__main__":
    asyncio.run(main())
