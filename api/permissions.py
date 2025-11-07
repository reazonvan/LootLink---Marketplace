"""
Кастомные permission классы для API с защитой от IDOR атак.
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


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
        if hasattr(obj, 'seller'):  # Listing
            return obj.seller == request.user
        elif hasattr(obj, 'user'):  # Profile и другие
            return obj.user == request.user
        elif hasattr(obj, 'reviewer'):  # Review
            return obj.reviewer == request.user
        elif hasattr(obj, 'sender'):  # Message
            return obj.sender == request.user
        
        # По умолчанию запрещаем
        return False


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
        return obj.reviewer == request.user


class IsConversationParticipant(permissions.BasePermission):
    """
    Разрешение только для участников беседы.
    Защита от доступа к чужим чатам.
    """
    
    def has_object_permission(self, request, view, obj):
        # Для Conversation
        if hasattr(obj, 'participant1') and hasattr(obj, 'participant2'):
            return request.user in [obj.participant1, obj.participant2]
        
        # Для Message - проверяем через conversation
        if hasattr(obj, 'conversation'):
            conversation = obj.conversation
            return request.user in [conversation.participant1, conversation.participant2]
        
        return False


class CanCreateReview(permissions.BasePermission):
    """
    Разрешение на создание отзыва.
    Пользователь может оставить отзыв только если у него была завершенная сделка.
    """
    
    def has_permission(self, request, view):
        # Для non-POST методов разрешаем (будет проверено в has_object_permission)
        if request.method != 'POST':
            return True
        
        # Для POST проверяем наличие прав в perform_create
        # Здесь просто разрешаем, детальная проверка будет в ViewSet
        return request.user and request.user.is_authenticated


class IsBuyerOrSeller(permissions.BasePermission):
    """
    Разрешение для покупателя или продавца в транзакции.
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'buyer') and hasattr(obj, 'seller'):
            return request.user in [obj.buyer, obj.seller]
        return False
