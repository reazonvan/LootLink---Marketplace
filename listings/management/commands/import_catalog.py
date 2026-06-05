"""
Импорт каталога игр и категорий из JSON.

Использование:
    python manage.py import_catalog
    python manage.py import_catalog --clean
    python manage.py import_catalog --dry-run
    python manage.py import_catalog --json path/to/games.json

Идемпотентен: повторный запуск обновит существующие записи (по external_id),
не создаст дубликатов. Флаг --clean удаляет всё перед загрузкой.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from listings.models import Category, Game, Listing
from listings.models_filters import CategoryFilter

# Маппинг ключевых слов в названии категории -> Bootstrap Icon.
# Перебирается по порядку, первое совпадение выигрывает.
ICON_RULES: list[tuple[str, str]] = [
    (r"\bаккаунт", "bi-person-circle"),
    (r"\bаkk?аун", "bi-person-circle"),
    (r"\bгем", "bi-gem"),
    (r"\bалмаз", "bi-gem"),
    (r"\bкристалл", "bi-gem"),
    (r"\bдиамант", "bi-gem"),
    (r"\bdiamond", "bi-gem"),
    (r"\bgem", "bi-gem"),
    (r"\bключ", "bi-key-fill"),
    (r"\bkey", "bi-key-fill"),
    (r"\bдонат", "bi-cash-coin"),
    (r"\bвалюта", "bi-coin"),
    (r"\bденьг", "bi-cash"),
    (r"\bcoin", "bi-coin"),
    (r"\bмонет", "bi-coin"),
    (r"\bgold", "bi-coin"),
    (r"\bзолот", "bi-coin"),
    (r"\bсеребр", "bi-circle-half"),
    (r"\bsilver", "bi-circle-half"),
    (r"\bруб", "bi-currency-exchange"),
    (r"\bпредмет", "bi-box-seam"),
    (r"\bитем", "bi-box-seam"),
    (r"\bitem", "bi-box-seam"),
    (r"\bскин", "bi-palette"),
    (r"\bskin", "bi-palette"),
    (r"\bкейс", "bi-archive-fill"),
    (r"\bcase", "bi-archive-fill"),
    (r"\bпрокачк", "bi-graph-up-arrow"),
    (r"\bбуст", "bi-rocket-takeoff"),
    (r"\bboost", "bi-rocket-takeoff"),
    (r"\bлевел", "bi-graph-up-arrow"),
    (r"\bкалибровк", "bi-bullseye"),
    (r"\bтренировк", "bi-mortarboard"),
    (r"\bобучен", "bi-mortarboard"),
    (r"\btraining", "bi-mortarboard"),
    (r"\bquest", "bi-flag-fill"),
    (r"\bквест", "bi-flag-fill"),
    (r"\bтаск", "bi-flag-fill"),
    (r"\braid", "bi-shield-shaded"),
    (r"\bрейд", "bi-shield-shaded"),
    (r"\bподписк", "bi-card-checklist"),
    (r"\bsubscription", "bi-card-checklist"),
    (r"\bbattle\s*pass", "bi-trophy"),
    (r"\bбатл\s*пасс", "bi-trophy"),
    (r"\bпасс", "bi-trophy"),
    (r"\bpass", "bi-trophy"),
    (r"\btwitch\s*drop", "bi-twitch"),
    (r"\bprime\s*gaming", "bi-twitch"),
    (r"\bgame\s*pass", "bi-controller"),
    (r"\bподарок", "bi-gift"),
    (r"\bgift", "bi-gift"),
    (r"\bпополнен", "bi-wallet2"),
    (r"\bбаланс", "bi-wallet2"),
    (r"\bкарт", "bi-credit-card"),
    (r"\bпромокод", "bi-ticket-perforated"),
    (r"\bpromo", "bi-ticket-perforated"),
    (r"\bактиваци", "bi-power"),
    (r"\bоффлайн", "bi-power"),
    (r"\boffline", "bi-power"),
    (r"\bonline", "bi-wifi"),
    (r"\bклан", "bi-people"),
    (r"\bclan", "bi-people"),
    (r"\bguild", "bi-people"),
    (r"\bинвайт", "bi-envelope"),
    (r"\binvite", "bi-envelope"),
    (r"\bреферал", "bi-share"),
    (r"\breferral", "bi-share"),
    (r"\bуслуг", "bi-tools"),
    (r"\bservice", "bi-tools"),
    (r"\bregion", "bi-globe"),
    (r"\bрегион", "bi-globe"),
    (r"\bсерв", "bi-hdd-network"),
    (r"\bserver", "bi-hdd-network"),
    (r"\bкуб", "bi-trophy"),
    (r"\bachievement", "bi-trophy-fill"),
    (r"\bдостижен", "bi-trophy-fill"),
    (r"\bmmr", "bi-bar-chart"),
    (r"\bранг", "bi-bar-chart"),
    (r"\brank", "bi-bar-chart"),
    (r"\bруна", "bi-magic"),
    (r"\brune", "bi-magic"),
    (r"\bpvp", "bi-crosshair"),
    (r"\bpve", "bi-shield-fill"),
    (r"\bferm", "bi-flower3"),
    (r"\bfarm", "bi-flower3"),
    (r"\bфарм", "bi-flower3"),
    (r"\bбосс", "bi-fire"),
    (r"\bboss", "bi-fire"),
    (r"\bdungeon", "bi-door-closed"),
    (r"\bподземел", "bi-door-closed"),
]


def pick_icon(category_name: str) -> str:
    text = (category_name or "").lower()
    for pattern, icon in ICON_RULES:
        if re.search(pattern, text):
            return icon
    return "bi-tag"


# Транслитерация для slug
TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def make_slug(name: str) -> str:
    transliterated = "".join(TRANSLIT.get(c, c) for c in (name or "").lower())
    s = slugify(transliterated)
    return s or "item"


def normalize(text: str) -> str:
    """Декодирует HTML-сущности (&#039; -> ') и зажимает пробелы."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


class Command(BaseCommand):
    help = "Импорт игр и категорий из JSON каталога"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--json",
            default="scripts/catalog_data/games.json",
            help="Путь к JSON со спарсенными данными",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Удалить все Listing/CategoryFilter/Category/Game перед импортом",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать что будет сделано, без записи в БД",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Импортировать только первые N игр (для тестов)",
        )

    def handle(self, *args, **opts) -> None:
        json_path = Path(opts["json"])
        if not json_path.exists():
            raise CommandError(f"Файл не найден: {json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        if opts["limit"]:
            data = data[: opts["limit"]]

        total_games = len(data)
        total_cats = sum(len(g["categories"]) for g in data)
        self.stdout.write(
            self.style.SUCCESS(f"[i] Загружено из JSON: {total_games} игр / {total_cats} категорий")
        )

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("[i] DRY-RUN — изменения в БД не пишутся"))
            self._preview(data, opts["clean"])
            return

        with transaction.atomic():
            if opts["clean"]:
                self._clean()
            self._import(data)

        # Сбрасываем кэш каталога — иначе пользователи увидят старое до 5 минут.
        try:
            from listings.signals import invalidate_catalog_cache

            invalidate_catalog_cache()
        except Exception:  # noqa: BLE001  # nosec
            pass

        self.stdout.write(self.style.SUCCESS("[OK] Импорт завершён"))
        self._summary()

    def _preview(self, data: list, do_clean: bool) -> None:
        if do_clean:
            self.stdout.write(
                f"  CLEAN: удалит {Listing.objects.count()} объявлений, "
                f"{CategoryFilter.objects.count()} фильтров, "
                f"{Category.objects.count()} категорий, {Game.objects.count()} игр"
            )
        new_g = updated_g = 0
        for g in data:
            qs = (
                Game.objects.filter(external_id=g["external_id"])
                if g["external_id"]
                else Game.objects.filter(name=g["name"])
            )
            if qs.exists():
                updated_g += 1
            else:
                new_g += 1
        self.stdout.write(
            f"  GAMES: новых {new_g}, обновлённых {updated_g} "
            f"(категорий ~ {sum(len(g['categories']) for g in data)})"
        )
        self.stdout.write("\n  Sample (first 3 games):")
        for g in data[:3]:
            self.stdout.write(f"    [{g['external_id']}] {g['name']}")
            for c in g["categories"][:5]:
                self.stdout.write(f"        - {c['name']} -> icon {pick_icon(c['name'])}")

    def _clean(self) -> None:
        # Соблюдаем порядок из-за FK с PROTECT (Listing.category)
        l_count = Listing.objects.count()
        f_count = CategoryFilter.objects.count()
        c_count = Category.objects.count()
        g_count = Game.objects.count()
        Listing.objects.all().delete()
        CategoryFilter.objects.all().delete()
        Category.objects.all().delete()
        # У Game.delete есть собственная проверка active listings — обходим напрямую через QuerySet
        Game.objects.all().delete()
        self.stdout.write(
            self.style.WARNING(
                f"[clean] удалено: {l_count} listings, {f_count} filters, "
                f"{c_count} categories, {g_count} games"
            )
        )

    def _import(self, data: list) -> None:
        existing_slugs: set[str] = set(Game.objects.values_list("slug", flat=True))
        created_g = updated_g = 0
        created_c = updated_c = 0

        for order, g in enumerate(data):
            game_name = normalize(g["name"])
            if not game_name:
                continue
            game_slug = self._unique_slug(make_slug(game_name), existing_slugs)
            game_defaults = {
                "name": game_name,
                "slug": game_slug,
                "is_active": True,
                "order": order,
            }
            if g.get("external_id"):
                game, created = Game.objects.update_or_create(
                    external_id=g["external_id"],
                    defaults=game_defaults,
                )
            else:
                game, created = Game.objects.update_or_create(
                    name=game_name,
                    defaults=game_defaults,
                )
            if created:
                created_g += 1
                existing_slugs.add(game.slug)
            else:
                updated_g += 1

            seen_cat_names_for_game: set[str] = set()
            for cat_order, c in enumerate(g["categories"]):
                cat_name = normalize(c["name"])
                if not cat_name or cat_name.lower() in seen_cat_names_for_game:
                    continue
                seen_cat_names_for_game.add(cat_name.lower())

                cat_slug = make_slug(cat_name)
                cat_defaults = {
                    "name": cat_name,
                    "slug": cat_slug,
                    "icon": pick_icon(cat_name),
                    "is_active": True,
                    "order": cat_order,
                }
                if c.get("external_id"):
                    cat, c_created = Category.objects.update_or_create(
                        game=game,
                        external_id=c["external_id"],
                        defaults=cat_defaults,
                    )
                else:
                    cat, c_created = Category.objects.update_or_create(
                        game=game,
                        name=cat_name,
                        defaults=cat_defaults,
                    )
                if c_created:
                    created_c += 1
                else:
                    updated_c += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[done] games: +{created_g} created, ~{updated_g} updated; "
                f"categories: +{created_c} created, ~{updated_c} updated"
            )
        )

    @staticmethod
    def _unique_slug(base: str, taken: set[str]) -> str:
        if base not in taken:
            return base
        i = 2
        while f"{base}-{i}" in taken:
            i += 1
        return f"{base}-{i}"

    def _summary(self) -> None:
        self.stdout.write("")
        self.stdout.write(
            f"  Итого в БД: {Game.objects.count()} игр, {Category.objects.count()} категорий"
        )
