"""
Django settings package для LootLink.

Структура:
- base.py        — общие настройки (читают .env)
- development.py — DEBUG, console email, без secure-cookies
- production.py  — Sentry, secure cookies, HSTS
- test.py        — fast hashers, in-memory cache, eager Celery

Использование:
    DJANGO_SETTINGS_MODULE=config.settings.development  # для разработки
    DJANGO_SETTINGS_MODULE=config.settings.production   # для прода
    DJANGO_SETTINGS_MODULE=config.settings.test         # для pytest

Этот __init__.py специально пустой. Если DJANGO_SETTINGS_MODULE=config.settings
(без явного env), Python попытается импортировать этот пакет и не найдёт
обычных настроек — нужно указать явный модуль.
"""
