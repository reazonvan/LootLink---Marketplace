"""
Custom storage backends for media files.

Разделяем публичный и приватный storage:
- PublicMediaStorage — аватары, картинки листингов, chat-images
- PrivateMediaStorage — KYC-документы, dispute evidence, financial attachments

В dev (USE_S3=False) — приватный storage пишет в media_private/ под
MEDIA_ROOT; раздачу делает отдельная защищённая view (не serve напрямую).
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def _file_system_private_storage():
    """Локальный приватный storage: media_private/ внутри BASE_DIR.

    URL пуст — файлы не должны раздаваться через MEDIA_URL.
    Доступ — через защищённую view с проверкой прав.
    """
    base = getattr(settings, "MEDIA_ROOT", None)
    if base is None:
        return FileSystemStorage(location="media_private")
    return FileSystemStorage(
        location=str(base) + "_private",
        base_url=None,  # никаких прямых URL
    )


# Локальный приватный storage (используется когда USE_S3=False)
private_local_storage = _file_system_private_storage()


def get_private_storage():
    """Фабрика приватного storage — выбирает S3-private или local."""
    if getattr(settings, "USE_S3", False):
        try:
            return PrivateMediaStorage()
        except Exception:
            return private_local_storage
    return private_local_storage


# S3 backends — импортируем условно, чтобы dev без boto3 не падал.
try:
    from storages.backends.s3boto3 import S3Boto3Storage

    class MediaStorage(S3Boto3Storage):
        """Публичный storage в S3: avatars, listing images, etc."""

        location = "media"
        file_overwrite = False
        default_acl = "public-read"

    class StaticStorage(S3Boto3Storage):
        """Static files в S3."""

        location = "static"
        default_acl = "public-read"

    class PrivateMediaStorage(S3Boto3Storage):
        """Приватный storage в S3: KYC, dispute evidence.

        default_acl=None — ACL не выставляется, бакет должен быть приватным.
        querystring_auth=True — выдача через signed URL.
        """

        location = "media_private"
        file_overwrite = False
        default_acl = None
        querystring_auth = True
        querystring_expire = 300  # 5 минут на signed URL

except ImportError:  # pragma: no cover
    # storages не установлен — заглушки, чтобы импорты не падали.
    MediaStorage = None
    StaticStorage = None
    PrivateMediaStorage = None
