"""
Импорт курированных фильтров (CategoryFilter + FilterOption) из JSON.

JSON формат:
[
  {
    "category_external_id": "1350",
    "category_hint": "...",  // только для логов
    "filters": [
      {
        "name": "Звание",
        "field_name": "rank",
        "filter_type": "select|multiselect|range|checkbox",
        "is_required": false,
        "options": ["Silver I", "Silver II", ...]   // для select/multiselect
      },
      ...
    ]
  },
  ...
]

Использование:
    python manage.py import_curated_filters
    python manage.py import_curated_filters --json path/to/file.json
    python manage.py import_curated_filters --replace   # удаляет существующие фильтры категории перед импортом
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from listings.models import Category
from listings.models_filters import CategoryFilter, FilterOption

VALID_TYPES = {"select", "multiselect", "range", "checkbox"}


class Command(BaseCommand):
    help = "Импорт курированных фильтров категорий из JSON"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--json",
            default="scripts/catalog_data/filters_curated.json",
            help="Путь к JSON с фильтрами",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Удалить существующие фильтры категории перед импортом",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать что будет сделано, не записывая в БД",
        )

    def handle(self, *args, **opts) -> None:
        json_path = Path(opts["json"])
        if not json_path.exists():
            raise CommandError(f"Файл не найден: {json_path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))

        total_filters = sum(len(b["filters"]) for b in data)
        self.stdout.write(
            self.style.SUCCESS(
                f"[i] Загружено: {len(data)} групп категорий, {total_filters} фильтров"
            )
        )

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("[i] DRY-RUN — записи не пишутся"))
            self._preview(data)
            return

        with transaction.atomic():
            stats = self._import(data, replace=opts["replace"])

        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Импорт завершён: "
                f"+{stats['filters_created']} фильтров, "
                f"~{stats['filters_updated']} обновлено, "
                f"+{stats['options_created']} опций, "
                f"-{stats['filters_deleted']} удалено (replace mode)"
            )
        )
        if stats["skipped_categories"]:
            self.stdout.write(
                self.style.WARNING(
                    f"[!] Пропущены (категории не найдены): {', '.join(stats['skipped_categories'])}"
                )
            )

    def _preview(self, data: list) -> None:
        for block in data:
            cat = Category.objects.filter(external_id=block["category_external_id"]).first()
            label = block.get("category_hint", "?")
            if cat:
                self.stdout.write(
                    f"  [{block['category_external_id']}] {label} -> {cat.game.name} > {cat.name}"
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{block['category_external_id']}] {label} -> CATEGORY NOT FOUND, would skip"
                    )
                )
            for f in block["filters"]:
                opt_count = len(f.get("options") or [])
                tail = f" ({opt_count} options)" if opt_count else ""
                self.stdout.write(f"      - {f['name']} [{f['filter_type']}]{tail}")

    def _import(self, data: list, replace: bool) -> dict:  # noqa: C901
        stats = {
            "filters_created": 0,
            "filters_updated": 0,
            "filters_deleted": 0,
            "options_created": 0,
            "skipped_categories": [],
        }

        for block in data:
            external_id = str(block.get("category_external_id", "")).strip()
            if not external_id:
                continue
            cat = Category.objects.filter(external_id=external_id).first()
            if not cat:
                hint = block.get("category_hint", external_id)
                stats["skipped_categories"].append(hint)
                continue

            if replace:
                deleted, _ = CategoryFilter.objects.filter(category=cat).delete()
                stats["filters_deleted"] += deleted

            for order, f in enumerate(block["filters"]):
                ftype = f.get("filter_type", "select")
                if ftype not in VALID_TYPES:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[!] {cat}: bad filter_type {ftype} for {f.get('name')}, skipped"
                        )
                    )
                    continue

                cf, created = CategoryFilter.objects.update_or_create(
                    category=cat,
                    field_name=f["field_name"],
                    defaults={
                        "name": f["name"],
                        "filter_type": ftype,
                        "is_required": bool(f.get("is_required", False)),
                        "is_active": True,
                        "order": order,
                    },
                )
                if created:
                    stats["filters_created"] += 1
                else:
                    stats["filters_updated"] += 1

                if ftype in {"select", "multiselect"}:
                    for opt_order, raw in enumerate(f.get("options") or []):
                        if isinstance(raw, dict):
                            value = raw.get("value", "").strip()
                            display = raw.get("display_name", "").strip()
                        else:
                            value = str(raw).strip()
                            display = ""
                        if not value:
                            continue
                        _, opt_created = FilterOption.objects.update_or_create(
                            filter=cf,
                            value=value,
                            defaults={
                                "display_name": display,
                                "order": opt_order,
                                "is_active": True,
                            },
                        )
                        if opt_created:
                            stats["options_created"] += 1

        return stats
