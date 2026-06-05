"""
Парсер сохранённой главной страницы funpay.com в games.json для
`python manage.py import_funpay_catalog`.

Использование:
    python scripts/parse_funpay_html.py "path/to/FunPay.html" [scripts/funpay_data/games.json]

Структура источника (funpay.com):
    .promo-game-item
        .game-title[data-id=<gameId>] > a[href=.../lots/<id>/]  -> игра
        ul.list-inline > li > a[href=.../lots/<catId>/]          -> категории

Игры на странице повторяются (секции «ваши игры» / «все игры», desktop/mobile,
.hidden-дубликаты), поэтому дедуплицируем по funpay_id игры и объединяем
категории. Результат — список вида:
    [{"funpay_id": "153", "name": "Brawl Stars",
      "categories": [{"funpay_id": "436", "name": "Аккаунты"}, ...]}, ...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

LOTS_RE = re.compile(r"/lots/(\d+)")


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    games: dict[str, dict] = {}

    for item in soup.select(".promo-game-item"):
        title = item.select_one(".game-title")
        link = title.select_one("a") if title else None
        if not link:
            continue
        name = link.get_text(strip=True)
        if not name:
            continue
        gid = (title.get("data-id") or "").strip()
        if not gid:
            m = LOTS_RE.search(link.get("href", ""))
            gid = m.group(1) if m else ""

        key = gid or name.lower()
        game = games.setdefault(key, {"funpay_id": gid, "name": name, "_cats": {}})

        for la in item.select("ul.list-inline li a"):
            cname = la.get_text(strip=True)
            if not cname:
                continue
            m = LOTS_RE.search(la.get("href", ""))
            cfp = m.group(1) if m else ""
            ckey = cfp or cname.lower()
            game["_cats"].setdefault(ckey, {"funpay_id": cfp, "name": cname})

    out = []
    for g in games.values():
        out.append(
            {
                "funpay_id": g["funpay_id"],
                "name": g["name"],
                "categories": list(g["_cats"].values()),
            }
        )
    out.sort(key=lambda x: x["name"].lower())
    return out


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: parse_funpay_html.py <source.html> [out.json]")
    src = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("scripts/funpay_data/games.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = parse(src.read_text(encoding="utf-8"))
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    total_cats = sum(len(g["categories"]) for g in data)
    print(f"games: {len(data)} | categories: {total_cats} | -> {out_path}")
    for g in data[:5]:
        print(f"  [{g['funpay_id']}] {g['name']} ({len(g['categories'])} cats)")


if __name__ == "__main__":
    main()
