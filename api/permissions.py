"""
Кастомные permission классы для API с защитой от IDOR атак.
"""

import logging

from rest_framework import permissions

logger = logging.getLogger(__name__)


def _user_id(request):
    """Безопасно достаём id пользователя для логов (или 'anon')."""
    u = getattr(request, "user", None)
    if u and getattr(u, "is_authenticated", False):
        return u.pk
    return "anon"


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение на редактирование только владельцем объекта.
    Защита от IDOR (Insecure Direct Object References).
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions для всех (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions только для владельца
        # Проверяем разные варианты ownership
        owner_pk = None
        granted = False
        if hasattr(obj, "seller"):  # Listing
            owner_pk = obj.seller_id
            granted = obj.seller_id == request.user.pk
        elif hasattr(obj, "user"):  # Profile и другие
            owner_pk = obj.user_id
            granted = obj.user_id == request.user.pk
        elif hasattr(obj, "reviewer"):  # Review
            owner_pk = obj.reviewer_id
            granted = obj.reviewer_id == request.user.pk
        elif hasattr(obj, "sender"):  # Message
            owner_pk = obj.sender_id
            granted = obj.sender_id == request.user.pk

        if not granted:
            logger.warning(
                "API IDOR blocked by IsOwnerOrReadOnly: user=%s obj=%s.%s owner=%s method=%s",
                _user_id(request),
                obj.__class__.__name__,
                getattr(obj, "pk", "?"),
                owner_pk,
                request.method,
            )
        return granted


class IsReviewerOrReadOnly(permissions.BasePermission):
    """
    Разрешение для отзывов - редактировать может только автор.
    Читать могут все аутентифицированные пользователи.
    """

    def has_object_permission(self, request, view, obj):
        # Читать могут все
        if request.method in permissions.SAFE_METHODS:
            return True

        # Редактировать/удалять может только автор отзыва
        granted = obj.reviewer_id == request.user.pk
        if not granted:
            logger.warning(
                "API IDOR blocked by IsReviewerOrReadOnly: user=%s review=%s reviewer=%s method=%s",
                _user_id(request),
                obj.pk,
                obj.reviewer_id,
                request.method,
            )
        return granted


class IsConversationParticipant(permissions.BasePermission):
    """
    Разрешение только для участников беседы.
    Защита от доступа к чужим чатам.
    """

    def has_object_permission(self, request, view, obj):
        # Для Conversation
        if hasattr(obj, "participant1") and hasattr(obj, "participant2"):
            granted = request.user.pk in (obj.participant1_id, obj.participant2_id)
            if not granted:
                logger.warning(
                    "API IDOR blocked on Conversation: user=%s conv=%s participants=(%s,%s)",
                    _user_id(request),
                    obj.pk,
                    obj.participant1_id,
                    obj.participant2_id,
                )
            return granted

        # Для Message - проверяем через conversation
        if hasattr(obj, "conversation"):
            conv = obj.conversation
            granted = request.user.pk in (conv.participant1_id, conv.participant2_id)
            if not granted:
                logger.warning(
                    "API IDOR blocked on Message: user=%s msg=%s conv=%s",
                    _user_id(request),
                    obj.pk,
                    conv.pk,
                )
            return granted

        logger.warning(
            "API IsConversationParticipant: unknown obj shape user=%s obj=%s",
            _user_id(request),
            obj.__class__.__name__,
        )
        return False


class CanCreateReview(permissions.BasePermission):
    """
    Разрешение на создание отзыва.
    Пользователь может оставить отзыв только если у него была завершенная сделка.
    """

    def has_permission(self, request, view):
        # Для non-POST методов разрешаем (будет проверено в has_object_permission)
        if request.method != "POST":
            return True

        # Для POST проверяем наличие прав в perform_create
        # Здесь просто разрешаем, детальная проверка будет в ViewSet
        return bool(request.user and request.user.is_authenticated)


class IsBuyerOrSeller(permissions.BasePermission):
    """
    Разрешение для покупателя или продавца в транзакции.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "buyer") and hasattr(obj, "seller"):
            granted = request.user.pk in (obj.buyer_id, obj.seller_id)
            if not granted:
                logger.warning(
                    "API IDOR blocked by IsBuyerOrSeller: user=%s obj=%s.%s buyer=%s seller=%s",
                    _user_id(request),
                    obj.__class__.__name__,
                    obj.pk,
                    obj.buyer_id,
                    obj.seller_id,
                )
            return granted
        logger.warning(
            "API IsBuyerOrSeller: unknown obj shape user=%s obj=%s",
            _user_id(request),
            obj.__class__.__name__,
        )
        return False
