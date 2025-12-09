# Telegram Event Forwarder Bot

MTProto userbot reads external channels, filters messages by city and category/keywords, and sends them to a Bot API bot that broadcasts to subscribed chats.

## Features
- Telethon userbot polls configured source channels.
- City filter with tolerant matching of inflected forms.
- Optional category filter (`categories`); falls back to `event_keywords` when categories are not set.
- Bot API side works via `getUpdates`/`sendMessage`; no webhooks needed.
- Subscriptions and offsets stored in SQLite.

## Requirements
- Python 3.10+
- Telegram `api_id` / `api_hash` (my.telegram.org -> API Development Tools)
- Bot API token (@BotFather)
- User account joined to source channels; bot must have write rights in target chats/channels.

## Install
```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

## Configure
1) Copy `config.example.yaml` to `config.yaml`.
2) Fill `api_id`, `api_hash`, `bot_token`, `channels`, `cities`.
3) Optional: `start_date` (YYYY-MM-DD) to ignore older posts.
4) Filtering:
   - If you set `categories`, each must have `name` and `keywords` (comma-separated string or list). A post must match at least one category.
   - If `categories` is empty, `event_keywords` are used as the keyword list (same format).
   - Optional `exclude_keywords`: if any of these match, the post is skipped **только если** не подошёл под категории/keywords (мягкая фильтрация рекламных слов).
   - Optional `hard_exclude_keywords`: если совпало любое, пост всегда пропускается (жёсткие маркеры вроде `реклама`, `erid`).
5) First run will ask for Telethon login (code via SMS/Telegram) and will create `user_session`.

### Example `config.yaml`
```yaml
api_id: 123456
api_hash: "XXX"
bot_token: "ZZZ"
user_session: "user_session"
poll_interval: 60
db_path: "data.db"
forward_with_link: true
start_date: "2024-12-01"
channels:
  - "sports_channel_1"
  - "https://t.me/sports_events_moscow"
cities:
  - name: "Москва"
    keywords: ["Москва", "Moscow", "MSK"]
  - name: "Санкт-Петербург"
    keywords: ["Санкт-Петербург", "СПб", "Питер", "Saint Petersburg", "Spb"]
categories:
  - name: "Бег"
    keywords: ["бег", "марафон", "забег"]
  - name: "Триатлон"
    keywords: ["триатлон", "ironman", "swimrun"]
# Skip messages that look like ads
exclude_keywords:
  - "реклама"
  - "промокод"
  - "скидка"
hard_exclude_keywords:
  - "erid"
  - "реклама!"
# If categories are omitted/empty, event_keywords are used instead:
event_keywords:
  - "марафон"
  - "забег"
```
Message passes if it contains any city keyword and (any category keyword or event keyword), and (if set) message date >= `start_date`.

## Run
```bash
python main.py
```

## Bot API commands
- `/start` — включить поиск/рассылку (ответ: «Идёт поиск...»).
- `/stop` — выключить поиск/рассылку (ответ: «Поиск закончен...»).
- `/status` — показать текущий статус поиска.
- `/refresh` — немедленно запустить ручной опрос источников без сброса оффсетов.

## Flow
1) Userbot polls sources every `poll_interval`, stores last IDs in `offsets`.
2) Text is checked for city hit, category/event keyword hit, and optional `start_date` cutoff.
3) Formatted message: `Анонс: <channel>\nГород: <city>\nКатегории: <...>\n\n<text>\n\nСсылка: <link>` (categories/link lines are added when available) is sent via Bot API to all subscribed chats.
4) Subscriptions live in `subscriptions`; offsets per source in `offsets`.
