"""
Reusable mixins для оптимизации Django views и предотвращения N+1 queries.
"""
from django.db.models import QuerySet


class OptimizedQueryMixin:
    """
    Mixin для автоматической оптимизации queryset с select_related и prefetch_related.
    Использовать в Class-Based Views.
    """
    
    # Переопределите в дочернем классе
    select_related_fields = []
    prefetch_related_fields = []
    
    def get_queryset(self):
        """Получить оптимизированный queryset."""
        queryset = super().get_queryset()
        
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        
        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        return queryset


class ListingOptimizedMixin:
    """
    Предустановленный mixin для Listing запросов.
    Автоматически добавляет seller, game, category.
    """
    select_related_fields = ['seller', 'seller__profile', 'game', 'category']


class PurchaseRequestOptimizedMixin:
    """
    Предустановленный mixin для PurchaseRequest запросов.
    Автоматически добавляет listing, buyer, seller.
    """
    select_related_fields = [
        'listing', 'listing__game', 'listing__seller',
        'buyer', 'buyer__profile',
        'seller', 'seller__profile'
    ]


class ConversationOptimizedMixin:
    """
    Предустановленный mixin для Conversation запросов.
    Автоматически добавляет participants и listing.
    """
    select_related_fields = [
        'participant1', 'participant1__profile',
        'participant2', 'participant2__profile',
        'listing', 'listing__game'
    ]
    

class ReviewOptimizedMixin:
    """
    Предустановленный mixin для Review запросов.
    Автоматически добавляет reviewer и reviewed_user.
    """
    select_related_fields = [
        'reviewer', 'reviewer__profile',
        'reviewed_user', 'reviewed_user__profile',
        'purchase_request', 'purchase_request__listing'
    ]


# Utility функции для function-based views
def optimize_listing_queryset(queryset: QuerySet) -> QuerySet:
    """
    Оптимизирует queryset для Listing.
    
    Usage:
        listings = optimize_listing_queryset(Listing.objects.filter(status='active'))
    """
    return queryset.select_related(
        'seller', 'seller__profile', 'game', 'category'
    )


def optimize_purchase_queryset(queryset: QuerySet) -> QuerySet:
    """
    Оптимизирует queryset для PurchaseRequest.
    
    Usage:
        purchases = optimize_purchase_queryset(PurchaseRequest.objects.filter(buyer=user))
    """
    return queryset.select_related(
        'listing', 'listing__game', 'listing__seller',
        'buyer', 'buyer__profile',
        'seller', 'seller__profile'
    )


def optimize_conversation_queryset(queryset: QuerySet) -> QuerySet:
    """
    Оптимизирует queryset для Conversation.
    
    Usage:
        conversations = optimize_conversation_queryset(
            Conversation.objects.filter(participant1=user)
        )
    """
    return queryset.select_related(
        'participant1', 'participant1__profile',
        'participant2', 'participant2__profile',
        'listing', 'listing__game'
    )


def optimize_review_queryset(queryset: QuerySet) -> QuerySet:
    """
    Оптимизирует queryset для Review.
    
    Usage:
        reviews = optimize_review_queryset(Review.objects.filter(reviewed_user=user))
    """
    return queryset.select_related(
        'reviewer', 'reviewer__profile',
        'reviewed_user', 'reviewed_user__profile',
        'purchase_request', 'purchase_request__listing'
    )

