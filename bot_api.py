import logging
from typing import Iterable

import aiohttp

logger = logging.getLogger("bot-api")


class BotApiClient:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def send_message(self, chat_id: int, text: str) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("sendMessage failed %s: %s", resp.status, body)
                    return False
                data = await resp.json()
                if not data.get("ok"):
                    logger.error("sendMessage error: %s", data)
                    return False
                return True

    async def broadcast(self, chat_ids: Iterable[int], text: str) -> None:
        for chat_id in chat_ids:
            ok = await self.send_message(chat_id, text)
            if not ok:
                logger.warning("Failed to send to %s", chat_id)
