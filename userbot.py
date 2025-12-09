import asyncio
import logging
import re
from typing import Awaitable, Callable, Dict, List

from telethon import TelegramClient
from telethon.errors import UserDeactivatedBanError
from telethon.tl.types import Channel

from bot_api import BotApiClient
from filters import contains_excluded, detect_categories, detect_city, is_event
from storage import get_last_id, update_last_id

logger = logging.getLogger("userbot")


def build_link(channel: Channel, message_id: int) -> str:
    username = getattr(channel, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"
    if getattr(channel, "id", None):
        return f"https://t.me/c/{abs(channel.id)}/{message_id}"
    return ""


def _make_hashtags(categories: List[str]) -> List[str]:
    tags = []
    for cat in categories:
        slug = re.sub(r"[^a-z0-9_а-яё]+", "", re.sub(r"\s+", "_", cat.lower()))
        if slug:
            tags.append(f"#{slug}")
    return tags


async def poll_sources(
    api_id: int,
    api_hash: str,
    user_session: str,
    channels: List[str],
    city_rules: List[Dict],
    category_rules: List[Dict],
    event_keywords: List[str],
    exclude_keywords: List[str],
    hard_exclude_keywords: List[str],
    forward_with_link: bool,
    poll_interval: int,
    db_path: str,
    bot_api: BotApiClient,
    get_chats_callable: Callable[[], Awaitable[List[int]]],
    start_date=None,
) -> None:
    async with TelegramClient(user_session, api_id, api_hash) as user_client:
        me = await user_client.get_me()
        logger.info("Userbot logged in as %s", me.username or me.id)

        while True:
            for source in channels:
                try:
                    await _process_source(
                        user_client,
                        source,
                        city_rules,
                        category_rules,
                        event_keywords,
                        exclude_keywords,
                        hard_exclude_keywords,
                        forward_with_link,
                        db_path,
                        bot_api,
                        get_chats_callable,
                        start_date,
                    )
                except UserDeactivatedBanError:
                    logger.error("Account is banned; stop polling.")
                    return
                except Exception:
                    logger.exception("Failed to poll source %s", source)
            await asyncio.sleep(poll_interval)


async def _process_source(
    client: TelegramClient,
    source: str,
    city_rules: List[Dict],
    category_rules: List[Dict],
    event_keywords: List[str],
    exclude_keywords: List[str],
    hard_exclude_keywords: List[str],
    forward_with_link: bool,
    db_path: str,
    bot_api: BotApiClient,
    get_chats_callable: Callable[[], Awaitable[List[int]]],
    start_date=None,
) -> None:
    entity = await client.get_entity(source)
    last_seen = await get_last_id(db_path, source)
    newest = last_seen

    async for msg in client.iter_messages(entity, min_id=last_seen, reverse=True):
        text = msg.message or ""
        if not text:
            continue
        if start_date:
            msg_date = msg.date
            if msg_date and msg_date.replace(tzinfo=None) < start_date:
                continue

        if contains_excluded(text, hard_exclude_keywords):
            continue

        city = detect_city(text, city_rules)
        categories: List[str] = []
        if category_rules:
            categories = detect_categories(text, category_rules)
            has_category = bool(categories)
        else:
            has_category = is_event(text, event_keywords)

        # Skip only if it looks excluded AND we did not classify as event/category.
        if contains_excluded(text, exclude_keywords) and not has_category:
            continue

        if city and has_category:
            link = build_link(entity, msg.id) if forward_with_link else ""
            channel_name = getattr(entity, "title", None) or getattr(entity, "username", None) or "Источник"
            pub_date = msg.date
            pub_date_str = pub_date.astimezone().strftime("%Y-%m-%d %H:%M %Z") if pub_date else ""
            hashtags = _make_hashtags(categories)

            parts = []
            if hashtags:
                parts.append(" ".join(hashtags))
            if pub_date_str:
                parts.append(pub_date_str)
            source_line = link or channel_name
            parts.append(source_line)
            parts.extend(["", "------------------------------", "", text.strip()])
            payload = "\n".join(parts).strip()
            chat_ids = await get_chats_callable()
            await bot_api.broadcast(chat_ids, payload)
        newest = max(newest, msg.id)

    if newest != last_seen:
        await update_last_id(db_path, source, newest)
