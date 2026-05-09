"""
Скрапер каталога FunPay: игры + их категории продаж (chips/lots).

Извлекает только структурные данные таксономии — имена игр и категорий —
для заполнения каталога LootLink. Не копирует описательный/маркетинговый
текст, иконки или дизайн.

Использование:
    python scripts/funpay_scraper.py games            # игры + категории
    python scripts/funpay_scraper.py filters <funpay_id> [<funpay_id>...]
    python scripts/funpay_scraper.py filters-all      # фильтры для всех игр (долго!)

Результаты пишутся в scripts/funpay_data/
"""
from __future__ import annotations

import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = "https://funpay.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}
DATA_DIR = Path("scripts/funpay_data")


def fetch(url: str, retries: int = 3) -> str:
    """GET с ретраями. Возвращает текст или поднимает исключение."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            last_err = RuntimeError(f"HTTP {r.status_code} for {url}")
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


# ---------------------------------------------------------------------------
# 1. Парсинг главной страницы — список игр + их категории
# ---------------------------------------------------------------------------

# FunPay рендерит главную как:
#   <div class="counter-list" data-section="lots">
#     <a class="counter-item" href="/lots/N/" data-section-id="...">
#       <div class="counter-param">Название игры</div>
#       <div class="counter-list-item">Категория 1</div>
#       <div class="counter-list-item">Категория 2</div>
#       ...
#     </a>
#   </div>

class HomeParser(HTMLParser):
    """Извлекает структуру: игра -> [категории] из главной FunPay."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.games: list[dict] = []
        self._stack: list[tuple[str, dict]] = []
        self._current_game: dict | None = None
        self._current_text_target: list[str] | None = None
        self._depth = 0
        self._game_depth = -1

    def _classes(self, attrs: list) -> list[str]:
        for k, v in attrs:
            if k == "class":
                return (v or "").split()
        return []

    def _attr(self, attrs: list, name: str) -> str:
        for k, v in attrs:
            if k == name:
                return v or ""
        return ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._depth += 1
        cls = self._classes(attrs)

        # Карточка игры — ссылка с классом counter-item или promo-game-item
        if tag == "a" and ("counter-item" in cls or "promo-game-item" in cls):
            href = self._attr(attrs, "href")
            self._current_game = {
                "funpay_id": "",
                "name": "",
                "url": href,
                "section": "lots" if "/lots/" in href else ("chips" if "/chips/" in href else ""),
                "categories": [],
            }
            m = re.search(r"/(?:lots|chips)/(\d+)", href)
            if m:
                self._current_game["funpay_id"] = m.group(1)
            self._game_depth = self._depth
            return

        if self._current_game is None:
            return

        # Заголовок (название игры) — div.counter-param или div.game-title
        if tag in ("div", "h3", "span"):
            if "counter-param" in cls or "game-title" in cls or "promo-game-item-title" in cls:
                self._current_text_target = []
                self._stack.append(("title", self._current_game))
                return
            if "counter-list-item" in cls or "promo-game-item-tag" in cls:
                self._current_text_target = []
                self._stack.append(("category", self._current_game))
                return

    def handle_endtag(self, tag: str) -> None:
        if self._stack and tag in ("div", "h3", "span"):
            kind, game = self._stack[-1]
            text = "".join(self._current_text_target or []).strip() if self._current_text_target else ""
            if text:
                if kind == "title" and not game["name"]:
                    game["name"] = text
                elif kind == "category":
                    game["categories"].append(text)
            self._stack.pop()
            self._current_text_target = None

        if tag == "a" and self._current_game is not None and self._depth == self._game_depth:
            if self._current_game["name"]:
                self.games.append(self._current_game)
            self._current_game = None
            self._game_depth = -1

        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._current_text_target is not None:
            self._current_text_target.append(data)


def parse_games_regex(html: str) -> list[dict]:
    """Парсинг главной FunPay через regex.

    Реальная структура:
        <div class="promo-game-item">
          <div class="game-title" data-id="N"><a href=".../lots/M/">Game Name</a></div>
          <ul class="list-inline" data-id="N">
            <li><a href=".../lots/X/">Категория</a></li>
            ...
          </ul>
        </div>
    """
    games: list[dict] = []

    pattern = re.compile(
        r'<div\s+class="promo-game-item"[^>]*>\s*'
        r'<div\s+class="game-title(?:\s+hidden)?"\s+data-id="(\d+)"[^>]*>'
        r'\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>\s*</div>'
        r'\s*<ul\s+class="list-inline(?:\s+hidden)?"[^>]*>(.*?)</ul>',
        re.IGNORECASE | re.DOTALL,
    )

    for m in pattern.finditer(html):
        data_id = m.group(1)
        game_url = m.group(2).strip()
        name = m.group(3).strip()
        ul_body = m.group(4)

        cats: list[dict] = []
        for c in re.finditer(
            r'<li[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
            ul_body,
            re.IGNORECASE,
        ):
            cat_url = c.group(1).strip()
            cat_name = c.group(2).strip()
            if cat_name:
                cat_id_match = re.search(r"/(?:lots|chips)/(\d+)", cat_url)
                cats.append(
                    {
                        "name": cat_name,
                        "url": cat_url,
                        "funpay_id": cat_id_match.group(1) if cat_id_match else "",
                        "section": "chips" if "/chips/" in cat_url else "lots",
                    }
                )

        m_id = re.search(r"/(?:lots|chips)/(\d+)", game_url)
        section = "chips" if "/chips/" in game_url else "lots"
        games.append(
            {
                "funpay_id": m_id.group(1) if m_id else "",
                "data_id": data_id,
                "name": name,
                "url": game_url,
                "section": section,
                "categories": cats,
            }
        )
    return games


def scrape_games() -> list[dict]:
    """Получить полный список игр + их категории."""
    print(f"[i] Fetching {BASE}/")
    html = fetch(BASE + "/")
    print(f"[i] Got {len(html):,} chars")

    games = parse_games_regex(html)
    print(f"[i] Regex parser: {len(games)} games")

    if not games:
        print("[i] Trying html.parser…")
        p = HomeParser()
        p.feed(html)
        games = p.games
        print(f"[i] html.parser: {len(games)} games")

    # Группировка дубликатов (одна игра может быть в lots И в chips)
    by_id: dict[str, dict] = {}
    for g in games:
        key = g["funpay_id"] or g["name"].lower()
        if key in by_id:
            existing = by_id[key]
            for c in g["categories"]:
                if c not in existing["categories"]:
                    existing["categories"].append(c)
        else:
            by_id[key] = g

    games = list(by_id.values())
    games.sort(key=lambda x: x["name"].lower())
    return games


# ---------------------------------------------------------------------------
# 2. Парсинг страницы игры — фильтры
# ---------------------------------------------------------------------------

def parse_filters(html: str) -> list[dict]:
    """
    На странице /lots/N/ есть таблица предложений с заголовком,
    содержащим фильтры (Server, Side, Rank, Trophies, и т.д.).
    Извлекаем имена столбцов фильтров и их возможные значения из <select>.
    """
    filters: list[dict] = []

    # FunPay использует <select name="..."><option value="...">Display</option>…</select>
    # для каждого фильтра в шапке таблицы предложений.
    select_pattern = re.compile(
        r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>',
        re.IGNORECASE | re.DOTALL,
    )
    label_pattern = re.compile(
        r'<label[^>]*for="([^"]+)"[^>]*>([^<]+)</label>',
        re.IGNORECASE,
    )

    # Сопоставление name -> human-readable label
    name_to_label: dict[str, str] = {}
    for m in label_pattern.finditer(html):
        # for ссылается на id, но часто id == name
        name_to_label[m.group(1).strip()] = m.group(2).strip()

    for m in select_pattern.finditer(html):
        name = m.group(1)
        body = m.group(2)
        if name in {"page", "sort", "currency", "lang"}:
            continue
        options: list[dict] = []
        for o in re.finditer(
            r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)</option>',
            body,
            re.IGNORECASE,
        ):
            value = o.group(1).strip()
            display = o.group(2).strip()
            if value and display and display.lower() not in {"все", "all", "—", "-"}:
                options.append({"value": value, "label": display})

        if options:
            filters.append(
                {
                    "field_name": name,
                    "label": name_to_label.get(name, name.replace("_", " ").title()),
                    "options": options,
                }
            )

    return filters


def scrape_filters(funpay_id: str) -> dict:
    url = f"{BASE}/lots/{funpay_id}/"
    print(f"[i] Fetching {url}")
    html = fetch(url)
    filters = parse_filters(html)
    print(f"[i]   {len(filters)} filters extracted")
    return {"funpay_id": funpay_id, "url": url, "filters": filters}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cmd = argv[1] if len(argv) > 1 else "games"

    if cmd == "games":
        games = scrape_games()
        out = DATA_DIR / "games.json"
        out.write_text(json.dumps(games, ensure_ascii=False, indent=2), encoding="utf-8")
        total_cats = sum(len(g["categories"]) for g in games)
        print(f"\n[OK] Saved {len(games)} games / {total_cats} categories -> {out}")
        if games:
            print("\nSample (first 5):")
            for g in games[:5]:
                cat_names = [c["name"] if isinstance(c, dict) else c for c in g["categories"][:6]]
                more = "..." if len(g["categories"]) > 6 else ""
                print(f"  [{g['funpay_id']}] {g['name']}: {', '.join(cat_names)}{more}")
        return 0

    if cmd == "filters":
        ids = argv[2:]
        if not ids:
            print("Usage: filters <funpay_id> [<funpay_id>...]")
            return 1
        results = []
        for fid in ids:
            try:
                results.append(scrape_filters(fid))
                time.sleep(1)
            except Exception as e:  # noqa: BLE001
                print(f"[!] {fid}: {e}")
        out = DATA_DIR / f"filters_{ids[0]}.json"
        if len(ids) > 1:
            out = DATA_DIR / "filters_batch.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[OK] Saved -> {out}")
        return 0

    if cmd == "filters-all":
        games_path = DATA_DIR / "games.json"
        if not games_path.exists():
            print("[!] Run `games` first to produce games.json")
            return 1
        games = json.loads(games_path.read_text(encoding="utf-8"))
        out = DATA_DIR / "filters_all.json"
        existing = {}
        if out.exists():
            existing = {x["funpay_id"]: x for x in json.loads(out.read_text(encoding="utf-8"))}
        for i, g in enumerate(games, 1):
            fid = g["funpay_id"]
            if not fid or fid in existing:
                continue
            try:
                existing[fid] = scrape_filters(fid)
            except Exception as e:  # noqa: BLE001
                print(f"[!] {fid} ({g['name']}): {e}")
            if i % 20 == 0:
                out.write_text(
                    json.dumps(list(existing.values()), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"[i] Checkpoint: {i}/{len(games)} -> {out}")
            time.sleep(0.8)
        out.write_text(
            json.dumps(list(existing.values()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n[OK] Saved {len(existing)} filter sets -> {out}")
        return 0

    print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
