import re
from typing import Dict, List, Optional, Pattern

CYRILLIC_RE = re.compile(r"[а-яё]", flags=re.IGNORECASE)


def _normalize_text(text: str) -> str:
    return text.lower().replace("ё", "е")


def _prepare_keywords(raw_keywords) -> List[str]:
    if isinstance(raw_keywords, str):
        raw_keywords = [kw.strip() for kw in raw_keywords.split(",") if kw.strip()]
    return [kw.strip() for kw in (raw_keywords or []) if kw and kw.strip()]


def _stem_cyrillic(token: str) -> str:
    # Drop a trailing vowel/soft sign to catch common case endings (Москва -> Москв-)
    while len(token) > 3 and token[-1] in "аяеёиоуыюьяъй":
        token = token[:-1]
    return token


def _build_keyword_pattern(keyword: str) -> Pattern:
    norm_kw = _normalize_text(keyword)
    tokens = [t for t in re.split(r"[\s\-]+", norm_kw) if t]
    token_patterns = []
    for token in tokens:
        if CYRILLIC_RE.search(token):
            stem = _stem_cyrillic(token)
            token_patterns.append(rf"{re.escape(stem)}[а-яё]*")
        else:
            token_patterns.append(re.escape(token))
    body = r"[\s\-]+".join(token_patterns) if token_patterns else re.escape(norm_kw)
    return re.compile(rf"\b{body}\b", flags=re.IGNORECASE)


def _match_patterns(text: str, patterns: List[Pattern]) -> bool:
    normalized = _normalize_text(text)
    return any(p.search(normalized) for p in patterns)


def _collect_patterns(keywords: List[str]) -> List[Pattern]:
    return [_build_keyword_pattern(kw) for kw in keywords]


def normalize_cities(cities_cfg: List[Dict]) -> List[Dict[str, List[str]]]:
    result = []
    for city in cities_cfg:
        name = city.get("name", "")
        keywords = _prepare_keywords(city.get("keywords"))
        if keywords:
            result.append({"name": name, "keywords": keywords, "patterns": _collect_patterns(keywords)})
    return result


def detect_city(text: str, city_rules: List[Dict]) -> Optional[str]:
    if not city_rules:
        return None
    for rule in city_rules:
        patterns = rule.get("patterns") or _collect_patterns(rule.get("keywords", []))
        if _match_patterns(text, patterns):
            return rule.get("name") or rule["keywords"][0]
    return None


def is_event(text: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    patterns = _collect_patterns(keywords)
    return _match_patterns(text, patterns)


def normalize_categories(categories_cfg: List[Dict]) -> List[Dict[str, List[str]]]:
    result = []
    for category in categories_cfg or []:
        name = category.get("name", "")
        keywords = _prepare_keywords(category.get("keywords"))
        if keywords:
            result.append({"name": name, "keywords": keywords, "patterns": _collect_patterns(keywords)})
    return result


def detect_categories(text: str, category_rules: List[Dict]) -> List[str]:
    hits = []
    for rule in category_rules or []:
        patterns = rule.get("patterns") or _collect_patterns(rule.get("keywords", []))
        if _match_patterns(text, patterns):
            hits.append(rule.get("name") or rule["keywords"][0])
    return hits


def contains_excluded(text: str, exclude_keywords: List[str]) -> bool:
    if not exclude_keywords:
        return False
    patterns = _collect_patterns(_prepare_keywords(exclude_keywords))
    return _match_patterns(text, patterns)
