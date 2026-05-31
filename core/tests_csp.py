"""Тесты CSP-заголовков и nonce-миграции.

Стратегия: enforcing-политика пока разрешает script 'unsafe-inline' (в шаблонах
ещё есть инлайн-обработчики on*=), а параллельный Content-Security-Policy-
Report-Only — строгий (nonce, без unsafe-inline) и репортит оставшиеся
нарушения, ничего не блокируя.
"""

import re

import pytest


@pytest.mark.django_db
def test_csp_enforcing_keeps_unsafe_inline_report_only_is_strict(client):
    resp = client.get("/")
    assert resp.status_code == 200

    enforce_script = re.search(r"script-src[^;]*", resp["Content-Security-Policy"]).group(0)
    ro_script = re.search(r"script-src[^;]*", resp["Content-Security-Policy-Report-Only"]).group(0)

    # Enforcing не должен ломать инлайн-обработчики — оставляем unsafe-inline
    # и НЕ добавляем nonce-source (иначе браузер проигнорирует unsafe-inline).
    assert "'unsafe-inline'" in enforce_script
    assert "'nonce-" not in enforce_script

    # Report-Only — строгий: nonce есть, unsafe-inline нет.
    assert "'unsafe-inline'" not in ro_script
    assert "'nonce-" in ro_script


@pytest.mark.django_db
def test_csp_nonce_is_injected_into_inline_scripts(client):
    resp = client.get("/")
    assert resp.status_code == 200

    nonce = re.search(r"'nonce-([\w\-]+)'", resp["Content-Security-Policy-Report-Only"]).group(1)

    # Тот же per-request nonce подставлен в инлайн-<script> страницы.
    assert f'nonce="{nonce}"'.encode() in resp.content
