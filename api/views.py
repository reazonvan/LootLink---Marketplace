"""
REST API ViewSets.
"""

import logging

from django.conf import settings
from django.db.models import Count, Q
from django.http import JsonResponse

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.models import CustomUser, Profile
from chat.models import Conversation, Message
from listings.models import Category, Game, Listing
from transactions.models import Review

from .permissions import (
    CanCreateReview,
    IsConversationParticipant,
    IsOwnerOrReadOnly,
    IsReviewerOrReadOnly,
)
from .serializers import (
    CategorySerializer,
    ConversationSerializer,
    GameSerializer,
    ListingSerializer,
    MessageSerializer,
    ProfileSerializer,
    ReviewSerializer,
    UserSerializer,
)
from .throttling import BurstRateThrottle, CreateRateThrottle, ModifyRateThrottle

logger = logging.getLogger(__name__)


def vapid_public_key(request):
    """Public endpoint for web-push VAPID key."""
    return JsonResponse({"public_key": getattr(settings, "VAPID_PUBLIC_KEY", "")})


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """API для игр."""

    queryset = Game.objects.filter(is_active=True).annotate(
        listing_count=Count("listings", filter=Q(listings__status="active"))
    )
    serializer_class = GameSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "listing_count", "created_at"]
    ordering = ["order", "name"]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для категорий."""

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["game"]
    ordering = ["game", "order", "name"]


class ListingViewSet(viewsets.ModelViewSet):
    """API для объявлений."""

    queryset = Listing.objects.filter(status="active").select_related(
        "seller", "seller__profile", "game", "category"
    )
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    throttle_classes = [BurstRateThrottle, CreateRateThrottle, ModifyRateThrottle]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["game", "category", "seller", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        listing = serializer.save(seller=self.request.user)
        logger.info(
            "API listing created: id=%s seller=%s game=%s price=%s",
            listing.pk,
            self.request.user.pk,
            listing.game_id,
            listing.price,
        )

    def perform_update(self, serializer):
        listing = serializer.save()
        logger.info("API listing updated: id=%s by user=%s", listing.pk, self.request.user.pk)

    def perform_destroy(self, instance):
        listing_pk = instance.pk
        instance.delete()
        logger.warning(
            "API listing deleted: id=%s by user=%s",
            listing_pk,
            self.request.user.pk,
        )

    @action(detail=True, methods=["post"])
    def favorite(self, request, pk=None):
        """Добавить/убрать из избранного."""
        listing = self.get_object()
        from listings.models import Favorite

        favorite, created = Favorite.objects.get_or_create(user=request.user, listing=listing)

        if not created:
            favorite.delete()
            logger.info(
                "API favorite removed: user=%s listing=%s",
                request.user.pk,
                listing.pk,
            )
            return Response({"favorited": False})

        logger.info(
            "API favorite added: user=%s listing=%s",
            request.user.pk,
            listing.pk,
        )
        return Response({"favorited": True})


class ReviewViewSet(viewsets.ModelViewSet):
    """API для отзывов."""

    queryset = Review.objects.select_related("reviewer", "reviewed_user")
    serializer_class = ReviewSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsReviewerOrReadOnly,
        CanCreateReview,
    ]
    throttle_classes = [BurstRateThrottle, CreateRateThrottle]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["reviewed_user", "rating"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        """Создать отзыв, проверив право пользователя оставить его."""
        # Проверяем что у пользователя есть завершенная сделка с reviewed_user
        reviewed_user = serializer.validated_data.get("reviewed_user")
        purchase_request = serializer.validated_data.get("purchase_request")

        # Проверка что пользователь - участник сделки
        if purchase_request:
            is_participant = (
                purchase_request.buyer == self.request.user
                or purchase_request.seller == self.request.user
            )
            if not is_participant:
                logger.warning(
                    "API review denied (not participant): user=%s pr=%s",
                    self.request.user.pk,
                    purchase_request.pk,
                )
                raise PermissionDenied("Вы не можете оставить отзыв для этой сделки.")

            # Проверка что сделка завершена
            if purchase_request.status != "completed":
                logger.warning(
                    "API review denied (pr not completed): user=%s pr=%s status=%s",
                    self.request.user.pk,
                    purchase_request.pk,
                    purchase_request.status,
                )
                raise PermissionDenied("Отзыв можно оставить только после завершения сделки.")

        review = serializer.save(reviewer=self.request.user)
        logger.info(
            "API review created: id=%s reviewer=%s reviewed=%s rating=%s pr=%s",
            review.pk,
            self.request.user.pk,
            getattr(reviewed_user, "pk", None),
            getattr(review, "rating", None),
            getattr(purchase_request, "pk", None),
        )


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """API для бесед."""

    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    throttle_classes = [BurstRateThrottle]

    def get_queryset(self):
        """Вернуть только беседы текущего пользователя (защита от IDOR)."""
        return Conversation.objects.filter(
            Q(participant1=self.request.user) | Q(participant2=self.request.user)
        ).select_related("participant1", "participant2", "listing")

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated, IsConversationParticipant],
    )
    def messages(self, request, pk=None):
        """Вернуть сообщения беседы — только участникам."""
        conversation = self.get_object()

        # Дополнительная проверка (IsConversationParticipant уже проверяет, но для безопасности)
        if conversation.participant1 != request.user and conversation.participant2 != request.user:
            # IDOR-попытка: запрос прошёл get_queryset, но участником не является.
            # Сохраняем для security-аудита.
            logger.warning(
                "API IDOR attempt on conversation.messages: user=%s conv=%s",
                request.user.pk,
                conversation.pk,
            )
            raise PermissionDenied("Вы не являетесь участником этой беседы.")

        messages = conversation.messages.select_related("sender").order_by("created_at")
        serializer = MessageSerializer(messages, many=True)
        logger.info(
            "API messages fetched: user=%s conv=%s count=%s",
            request.user.pk,
            conversation.pk,
            len(serializer.data),
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsConversationParticipant],
    )
    def send_message(self, request, pk=None):
        """Отправить сообщение в беседу — только участникам."""
        conversation = self.get_object()

        # Проверка что пользователь - участник беседы
        if conversation.participant1 != request.user and conversation.participant2 != request.user:
            logger.warning(
                "API IDOR attempt on conversation.send_message: user=%s conv=%s",
                request.user.pk,
                conversation.pk,
            )
            raise PermissionDenied("Вы не можете отправлять сообщения в эту беседу.")

        content = request.data.get("content", "").strip()
        if not content:
            logger.info(
                "API send_message rejected (empty): user=%s conv=%s",
                request.user.pk,
                conversation.pk,
            )
            return Response(
                {"error": "Сообщение не может быть пустым"}, status=status.HTTP_400_BAD_REQUEST
            )

        message = Message.objects.create(
            conversation=conversation, sender=request.user, content=content
        )
        logger.info(
            "API message created: id=%s conv=%s sender=%s length=%s",
            message.pk,
            conversation.pk,
            request.user.pk,
            len(content),
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
