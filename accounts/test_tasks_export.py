"""Тесты Celery-задач accounts/tasks_export.py — GDPR-экспорт.

Покрывают:
- generate_data_export: успешный happy-path с записью ZIP, email и статусом
- generate_data_export: ошибка → статус failed, retry
- cleanup_old_exports: удаление старых файлов + записей
"""

import os
import tempfile
import zipfile
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import pytest

from accounts.models_export import DataExportRequest
from accounts.tasks_export import cleanup_old_exports, generate_data_export


@pytest.fixture
def export_dir(tmp_path, settings):
    """Изолированный MEDIA_ROOT для ZIP-файлов экспорта."""
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


# ─────────────────────────────────────────────────────────────────────
# generate_data_export — happy path
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_generate_data_export_happy_path(verified_user, export_dir, settings):
    """Успешный экспорт: ZIP создан, email отправлен, статус completed."""
    settings.SITE_URL = "https://test.local"
    req = DataExportRequest.objects.create(user=verified_user, status="pending")

    with patch("accounts.tasks_export.send_mail") as mock_mail:
        result = generate_data_export(req.id)

    req.refresh_from_db()
    assert req.status == "completed"
    assert req.completed_at is not None
    assert req.file_path
    assert os.path.exists(req.file_path)

    # ZIP содержит data.json и README.txt
    with zipfile.ZipFile(req.file_path) as zf:
        names = zf.namelist()
        assert "data.json" in names
        assert "README.txt" in names

    # Email отправлен с правильным получателем
    assert mock_mail.called
    assert mock_mail.call_args.kwargs["recipient_list"] == [verified_user.email]
    assert verified_user.username in mock_mail.call_args.kwargs["message"]

    assert "Export completed" in result


@pytest.mark.django_db
def test_generate_data_export_includes_listings_in_json(
    verified_user,
    listing_factory,
    export_dir,
    settings,
):
    """В data.json попадают объявления пользователя."""
    import json

    settings.SITE_URL = "https://test.local"
    listing = listing_factory(verified_user, title="My Test Item")
    req = DataExportRequest.objects.create(user=verified_user, status="pending")

    with patch("accounts.tasks_export.send_mail"):
        generate_data_export(req.id)

    req.refresh_from_db()
    with zipfile.ZipFile(req.file_path) as zf:
        with zf.open("data.json") as f:
            data = json.loads(f.read().decode())

    titles = [item["title"] for item in data["listings"]]
    assert "My Test Item" in titles


# ─────────────────────────────────────────────────────────────────────
# generate_data_export — error path
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_generate_data_export_marks_failed_on_error(verified_user, export_dir):
    """При ошибке внутри задачи запись помечается failed, и задача делает retry."""
    req = DataExportRequest.objects.create(user=verified_user, status="pending")

    # Заставляем generate_export_data упасть
    with patch(
        "accounts.views_export.generate_export_data",
        side_effect=RuntimeError("disk full"),
    ):
        with pytest.raises(Exception):
            generate_data_export(req.id)

    req.refresh_from_db()
    assert req.status == "failed"
    assert "disk full" in (req.error_message or "")


# ─────────────────────────────────────────────────────────────────────
# cleanup_old_exports
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_cleanup_old_exports_removes_files_and_rows(verified_user, tmp_path):
    """Старые экспорты (>7 дней) удаляются с диска и из БД."""
    # Свежий экспорт — не трогаем
    fresh_file = tmp_path / "fresh.zip"
    fresh_file.write_text("fresh")
    fresh_req = DataExportRequest.objects.create(
        user=verified_user,
        status="completed",
        file_path=str(fresh_file),
    )

    # Старый экспорт — должен удалиться
    old_file = tmp_path / "old.zip"
    old_file.write_text("old")
    old_req = DataExportRequest.objects.create(
        user=verified_user,
        status="completed",
        file_path=str(old_file),
    )
    DataExportRequest.objects.filter(pk=old_req.pk).update(
        created_at=timezone.now() - timedelta(days=8),
    )

    result = cleanup_old_exports()

    assert "1" in result
    assert fresh_file.exists()
    assert not old_file.exists()
    assert DataExportRequest.objects.filter(pk=fresh_req.pk).exists()
    assert not DataExportRequest.objects.filter(pk=old_req.pk).exists()


@pytest.mark.django_db
def test_cleanup_old_exports_handles_missing_file(verified_user, tmp_path):
    """Если file_path указан, но файла нет — запись всё равно удаляется без ошибки."""
    ghost_path = str(tmp_path / "never_existed.zip")
    req = DataExportRequest.objects.create(
        user=verified_user,
        status="completed",
        file_path=ghost_path,
    )
    DataExportRequest.objects.filter(pk=req.pk).update(
        created_at=timezone.now() - timedelta(days=10),
    )

    result = cleanup_old_exports()

    # deleted_count считает только файлы — он 0, но запись из БД должна уйти
    assert "Deleted" in result
    assert not DataExportRequest.objects.filter(pk=req.pk).exists()
