import aiosqlite
from typing import List


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS offsets (
                source TEXT PRIMARY KEY,
                last_id INTEGER NOT NULL
            )
            """
        )
        await db.commit()


async def set_subscription(db_path: str, chat_id: int, enabled: bool) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO subscriptions(chat_id, enabled)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET enabled=excluded.enabled
            """,
            (chat_id, int(enabled)),
        )
        await db.commit()


async def get_enabled_chats(db_path: str) -> List[int]:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT chat_id FROM subscriptions WHERE enabled = 1")
        rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def get_last_id(db_path: str, source: str) -> int:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT last_id FROM offsets WHERE source = ?", (source,))
        row = await cursor.fetchone()
    return row[0] if row else 0


async def update_last_id(db_path: str, source: str, last_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO offsets(source, last_id)
            VALUES (?, ?)
            ON CONFLICT(source) DO UPDATE SET last_id=excluded.last_id
            """,
            (source, last_id),
        )
        await db.commit()
