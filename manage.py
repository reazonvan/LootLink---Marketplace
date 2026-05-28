#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Run administrative tasks.

    Безопасный default: development settings разрешены только если явно
    задан DJANGO_ENV=dev/development/local. В production DJANGO_SETTINGS_MODULE
    должен указывать на config.settings.production — иначе AssertionError.
    Это защита от случайного запуска прод-сервера с MD5-хешером.
    """
    django_env = os.environ.get("DJANGO_ENV", "").lower()
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")

    if not settings_module:
        if django_env in ("dev", "development", "local"):
            settings_module = "config.settings.development"
        elif django_env in ("test", "testing", "ci"):
            settings_module = "config.settings.test"
        elif django_env in ("prod", "production"):
            settings_module = "config.settings.production"
        else:
            raise RuntimeError(
                "DJANGO_SETTINGS_MODULE не задан и DJANGO_ENV не распознан. "
                "Задайте одно из: DJANGO_ENV=dev|test|prod ИЛИ "
                "DJANGO_SETTINGS_MODULE=config.settings.{development|test|production}. "
                "Это защита от случайного запуска prod с dev-настройками (MD5-хешер)."
            )
        os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
