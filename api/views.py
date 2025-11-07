"""
REST API ViewSets.
"""
from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
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
from .throttling import BurstRateThrottle, CreateRateThrottle, ModifyRateThrottle
from .permissions import (
    IsOwnerOrReadOnly, IsReviewerOrReadOnly, IsConversationParticipant,
    CanCreateReview
)


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
    throttle_classes = [BurstRateThrottle, CreateRateThrottle, ModifyRateThrottle]
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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsReviewerOrReadOnly, CanCreateReview]
    throttle_classes = [BurstRateThrottle, CreateRateThrottle]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['reviewed_user', 'rating']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """
        Создание отзыва с проверкой что пользователь имеет право его оставить.
        """
        # Проверяем что у пользователя есть завершенная сделка с reviewed_user
        reviewed_user = serializer.validated_data.get('reviewed_user')
        purchase_request = serializer.validated_data.get('purchase_request')
        
        # Проверка что пользователь - участник сделки
        if purchase_request:
            is_participant = (
                purchase_request.buyer == self.request.user or
                purchase_request.seller == self.request.user
            )
            if not is_participant:
                raise PermissionDenied('Вы не можете оставить отзыв для этой сделки.')
            
            # Проверка что сделка завершена
            if purchase_request.status != 'completed':
                raise PermissionDenied('Отзыв можно оставить только после завершения сделки.')
        
        serializer.save(reviewer=self.request.user)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для бесед"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    throttle_classes = [BurstRateThrottle]
    
    def get_queryset(self):
        """
        Возвращает только беседы текущего пользователя.
        Защита от IDOR - пользователь не может получить чужие беседы.
        """
        return Conversation.objects.filter(
            Q(participant1=self.request.user) | Q(participant2=self.request.user)
        ).select_related('participant1', 'participant2', 'listing')
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsConversationParticipant])
    def messages(self, request, pk=None):
        """
        Получить сообщения беседы.
        Только участники беседы могут видеть сообщения.
        """
        conversation = self.get_object()
        
        # Дополнительная проверка (IsConversationParticipant уже проверяет, но для безопасности)
        if conversation.participant1 != request.user and conversation.participant2 != request.user:
            raise PermissionDenied('Вы не являетесь участником этой беседы.')
        
        messages = conversation.messages.select_related('sender').order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsConversationParticipant])
    def send_message(self, request, pk=None):
        """
        Отправить сообщение в беседу.
        Только участники беседы могут отправлять сообщения.
        """
        conversation = self.get_object()
        
        # Проверка что пользователь - участник беседы
        if conversation.participant1 != request.user and conversation.participant2 != request.user:
            raise PermissionDenied('Вы не можете отправлять сообщения в эту беседу.')
        
        content = request.data.get('content', '').strip()
        if not content:
            return Response(
                {'error': 'Сообщение не может быть пустым'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

