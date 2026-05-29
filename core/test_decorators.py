"""Тесты core/decorators.py — permission-декораторы + rate-limit.

Покрывают:
- owner_required / admin_required / moderator_required / verified_required:
  redirect для не имеющих прав, проход для имеющих
- staff_member_required: staff + moderator + superuser
- require_2fa: staff без 2FA → redirect, staff с 2FA → проход
- api_rate_limit: разрешает первые N, режет последующие
- check_rate_limit: атомарный счётчик cache.incr
"""

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory

import pytest

from core.decorators import (
    admin_required,
    api_rate_limit,
    check_rate_limit,
    moderator_required,
    owner_required,
    require_2fa,
    staff_member_required,
    verified_required,
)


def _attach_messages(request):
    """Подключаем messages storage — иначе decorator messages.error падает."""
    setattr(request, "session", "session")
    setattr(request, "_messages", FallbackStorage(request))
    return request


@pytest.fixture
def rf():
    return RequestFactory()


def _ok_view(request, *a, **kw):
    return HttpResponse("ok")


# ─────────────────────────────────────────────────────────────────────
# owner_required
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_owner_required_redirects_for_non_superuser(rf, verified_user):
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = owner_required(_ok_view)(request)
    assert resp.status_code == 302  # redirect


@pytest.mark.django_db
def test_owner_required_passes_for_superuser(rf, verified_user):
    verified_user.is_superuser = True
    verified_user.save(update_fields=["is_superuser"])
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = owner_required(_ok_view)(request)
    assert resp.status_code == 200
    assert resp.content == b"ok"


# ─────────────────────────────────────────────────────────────────────
# admin_required
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_admin_required_redirects_for_non_staff(rf, verified_user):
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = admin_required(_ok_view)(request)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_admin_required_passes_for_staff(rf, verified_user):
    verified_user.is_staff = True
    verified_user.save(update_fields=["is_staff"])
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = admin_required(_ok_view)(request)
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# moderator_required
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_moderator_required_passes_for_profile_moderator(rf, verified_user):
    verified_user.profile.is_moderator = True
    verified_user.profile.save()
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = moderator_required(_ok_view)(request)
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# verified_required
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_verified_required_redirects_unverified(rf, unverified_user):
    request = rf.get("/")
    request.user = unverified_user
    _attach_messages(request)

    resp = verified_required(_ok_view)(request)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_verified_required_passes_verified(rf, verified_user):
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = verified_required(_ok_view)(request)
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# staff_member_required
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_staff_member_required_blocks_regular_user(rf, verified_user):
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = staff_member_required(_ok_view)(request)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_staff_member_required_passes_for_superuser(rf, verified_user):
    verified_user.is_superuser = True
    verified_user.save(update_fields=["is_superuser"])
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = staff_member_required(_ok_view)(request)
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# require_2fa
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_require_2fa_lets_regular_user_through(rf, verified_user):
    """Non-staff не блокируются — 2FA нужно только привилегированным."""
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = require_2fa(_ok_view)(request)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_require_2fa_blocks_staff_without_2fa(rf, verified_user):
    """Staff без 2FA → redirect на setup."""
    verified_user.is_staff = True
    verified_user.save(update_fields=["is_staff"])
    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = require_2fa(_ok_view)(request)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_require_2fa_allows_staff_with_2fa(rf, verified_user):
    """Staff с подтверждённым TOTP проходит."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    verified_user.is_staff = True
    verified_user.save(update_fields=["is_staff"])
    TOTPDevice.objects.create(user=verified_user, name="t", confirmed=True)

    request = rf.get("/")
    request.user = verified_user
    _attach_messages(request)

    resp = require_2fa(_ok_view)(request)
    assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# api_rate_limit
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_api_rate_limit_allows_first_n(rf, verified_user):
    """Первые N запросов проходят."""
    request = rf.get("/")
    request.user = verified_user

    @api_rate_limit(max_requests=3, time_window=60)
    def view(request):
        return JsonResponse({"ok": True})

    for _ in range(3):
        resp = view(request)
        assert resp.status_code == 200


@pytest.mark.django_db
def test_api_rate_limit_blocks_n_plus_one(rf, verified_user):
    """Запрос N+1 возвращает 429."""
    request = rf.get("/")
    request.user = verified_user

    @api_rate_limit(max_requests=2, time_window=60)
    def view(request):
        return JsonResponse({"ok": True})

    view(request)
    view(request)
    resp = view(request)
    assert resp.status_code == 429


@pytest.mark.django_db
def test_api_rate_limit_separates_anon_by_ip(rf):
    """Анонимные раздельны по IP."""

    @api_rate_limit(max_requests=1, time_window=60)
    def view(request):
        return JsonResponse({"ok": True})

    r1 = rf.get("/", REMOTE_ADDR="1.1.1.1")
    r1.user = AnonymousUser()
    r2 = rf.get("/", REMOTE_ADDR="2.2.2.2")
    r2.user = AnonymousUser()

    assert view(r1).status_code == 200
    assert view(r2).status_code == 200
    # Каждый из них исчерпал свой лимит
    assert view(r1).status_code == 429


# ─────────────────────────────────────────────────────────────────────
# check_rate_limit
# ─────────────────────────────────────────────────────────────────────


def test_check_rate_limit_first_call_allowed():
    allowed, count = check_rate_limit("test:rl:first", 3, 60)
    assert allowed is True
    assert count == 1


def test_check_rate_limit_blocks_after_limit():
    """N допустимых, N+1 — нет."""
    key = "test:rl:over"
    for _ in range(3):
        allowed, _ = check_rate_limit(key, 3, 60)
        assert allowed is True
    allowed, count = check_rate_limit(key, 3, 60)
    assert allowed is False
    assert count == 4
