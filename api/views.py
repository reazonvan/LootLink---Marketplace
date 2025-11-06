"""
REST API ViewSets.
"""
from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from accounts.models import CustomUser, Profile
from listings.models import Listing, Game, Category
from transactions.models import Review
from chat.models import Conversation, Message
from .serializers import (
    UserSerializer, ProfileSerializer, GameSerializer, CategorySerializer,
    ListingSerializer, ReviewSerializer, MessageSerializer, ConversationSerializer
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Разрешение на редактирование только владельцем"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if hasattr(obj, 'seller'):
            return obj.seller == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """API для игр"""
    queryset = Game.objects.filter(is_active=True).annotate(
        listing_count=Count('listings', filter=Q(listings__status='active'))
    )
    serializer_class = GameSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'listing_count', 'created_at']
    ordering = ['order', 'name']


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для категорий"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['game']
    ordering = ['game', 'order', 'name']


class ListingViewSet(viewsets.ModelViewSet):
    """API для объявлений"""
    queryset = Listing.objects.filter(status='active').select_related(
        'seller', 'seller__profile', 'game', 'category'
    )
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['game', 'category', 'seller', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)
    
    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        """Добавить/убрать из избранного"""
        listing = self.get_object()
        from listings.models import Favorite
        
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing
        )
        
        if not created:
            favorite.delete()
            return Response({'favorited': False})
        
        return Response({'favorited': True})


class ReviewViewSet(viewsets.ModelViewSet):
    """API для отзывов"""
    queryset = Review.objects.select_related('reviewer', 'reviewed_user')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['reviewed_user', 'rating']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для бесед"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(
            Q(participant1=self.request.user) | Q(participant2=self.request.user)
        ).select_related('participant1', 'participant2', 'listing')
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Получить сообщения беседы"""
        conversation = self.get_object()
        messages = conversation.messages.select_related('sender').order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Отправить сообщение"""
        conversation = self.get_object()
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=request.data.get('content', '')
        )
        
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

