import asyncio
import logging

import aiohttp

from bot_api import BotApiClient
from config import load_config
from filters import normalize_categories, normalize_cities
from storage import get_enabled_chats, init_db, set_subscription
from userbot import poll_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


async def handle_commands(bot_api: BotApiClient, db_path: str, refresh_event: asyncio.Event) -> None:
    """Bot API long-polling for /start, /stop, /status, /refresh."""
    last_update_id = 0
    base_url = bot_api.base_url

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                params = {"timeout": 50, "offset": last_update_id + 1}
                async with session.get(f"{base_url}/getUpdates", params=params, timeout=60) as resp:
                    data = await resp.json()

                if not data.get("ok"):
                    logger.error("getUpdates error: %s", data)
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    message = update.get("message") or update.get("channel_post")
                    if not message:
                        continue
                    chat_id = message["chat"]["id"]
                    text = (message.get("text") or "").strip()

                    if text.startswith("/start"):
                        await set_subscription(db_path, chat_id, True)
                        await bot_api.send_message(chat_id, "Идёт поиск событий. Чтобы остановить — /stop.")
                    elif text.startswith("/stop"):
                        await set_subscription(db_path, chat_id, False)
                        await bot_api.send_message(chat_id, "Поиск закончен. Чтобы возобновить — /start.")
                    elif text.startswith("/status"):
                        subs = await get_enabled_chats(db_path)
                        status = "включен" if chat_id in subs else "выключен"
                        await bot_api.send_message(chat_id, f"Статус поиска: {status}")
                    elif text.startswith("/refresh"):
                        refresh_event.set()
                        await bot_api.send_message(chat_id, "Обновление запущено, проверяю новые посты.")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Command polling failed, retrying...")
                await asyncio.sleep(5)


async def main() -> None:
    cfg = load_config()
    city_rules = normalize_cities(cfg.cities)
    category_rules = normalize_categories(cfg.categories)
    event_keywords = [kw.lower() for kw in cfg.event_keywords]
    exclude_keywords = [kw.lower() for kw in cfg.exclude_keywords]
    hard_exclude_keywords = [kw.lower() for kw in cfg.hard_exclude_keywords]
    start_date = cfg.start_date

    await init_db(cfg.db_path)
    bot_api = BotApiClient(cfg.bot_token)

    refresh_event = asyncio.Event()

    userbot_task = asyncio.create_task(
        poll_sources(
            api_id=cfg.api_id,
            api_hash=cfg.api_hash,
            user_session=cfg.user_session,
            channels=cfg.channels,
            city_rules=city_rules,
            category_rules=category_rules,
            event_keywords=event_keywords,
            exclude_keywords=exclude_keywords,
            hard_exclude_keywords=hard_exclude_keywords,
            refresh_event=refresh_event,
            forward_with_link=cfg.forward_with_link,
            poll_interval=cfg.poll_interval,
            db_path=cfg.db_path,
            bot_api=bot_api,
            get_chats_callable=lambda: get_enabled_chats(cfg.db_path),
            start_date=start_date,
        )
    )

    commands_task = asyncio.create_task(handle_commands(bot_api, cfg.db_path, refresh_event))

    logger.info("Service started.")
    await asyncio.gather(userbot_task, commands_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
