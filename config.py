import os
from datetime import datetime
import yaml

DEFAULT_CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")

DEFAULT_EVENT_KEYWORDS = [
    "турнир",
    "матч",
    "игра",
    "забег",
    "марафон",
    "чемпионат",
    "соревнования",
    "кубок",
    "регистрация",
    "дистанция",
    "старт",
    "финиш",
]


class Config:
    def __init__(self, data: dict):
        self.api_id = int(data.get("api_id") or 0)
        self.api_hash = data.get("api_hash") or ""
        self.bot_token = data.get("bot_token") or ""
        self.user_session = data.get("user_session", "user_session")
        self.poll_interval = int(data.get("poll_interval", 60))
        self.db_path = data.get("db_path", "data.db")
        self.forward_with_link = bool(data.get("forward_with_link", True))
        self.channels = data.get("channels", []) or []
        self.cities = data.get("cities", []) or []
        self.categories = data.get("categories", []) or []
        self.event_keywords = data.get("event_keywords", []) or DEFAULT_EVENT_KEYWORDS
        self.exclude_keywords = data.get("exclude_keywords", []) or []
        self.hard_exclude_keywords = data.get("hard_exclude_keywords", []) or []
        self.start_date = self._parse_date(data.get("start_date"))

        if not (self.api_id and self.api_hash and self.bot_token):
            raise RuntimeError("api_id, api_hash, bot_token are required in config.yaml")

    @staticmethod
    def _parse_date(val):
        if not val:
            return None
        try:
            return datetime.fromisoformat(str(val))
        except Exception as exc:
            raise RuntimeError(f"Invalid start_date format: {val} (use YYYY-MM-DD)") from exc


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Config:
    if not os.path.exists(path):
        raise RuntimeError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Config(data)
