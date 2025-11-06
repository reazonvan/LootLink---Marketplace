"""
Serializers для REST API.
"""
from rest_framework import serializers
from accounts.models import CustomUser, Profile
from listings.models import Listing, Game, Category
from transactions.models import PurchaseRequest, Review
from chat.models import Conversation, Message


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class ProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля"""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'username', 'avatar', 'bio', 'rating', 
            'total_sales', 'total_purchases', 'is_verified'
        ]
        read_only_fields = ['rating', 'total_sales', 'total_purchases', 'is_verified']


class GameSerializer(serializers.ModelSerializer):
    """Сериализатор игры"""
    listing_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Game
        fields = ['id', 'name', 'slug', 'description', 'icon', 'listing_count']
        read_only_fields = ['id', 'slug']


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор категории"""
    game_name = serializers.CharField(source='game.name', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'game', 'game_name', 'icon', 'order']
        read_only_fields = ['id', 'slug']


class ListingSerializer(serializers.ModelSerializer):
    """Сериализатор объявления"""
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    seller_rating = serializers.DecimalField(
        source='seller.profile.rating', 
        max_digits=3, 
        decimal_places=2, 
        read_only=True
    )
    game_name = serializers.CharField(source='game.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'price', 'image', 'status',
            'game', 'game_name', 'category', 'category_name',
            'seller', 'seller_username', 'seller_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'seller', 'created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор отзыва"""
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    reviewed_user_username = serializers.CharField(source='reviewed_user.username', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'purchase_request', 'reviewer', 'reviewer_username',
            'reviewed_user', 'reviewed_user_username',
            'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'reviewer', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор сообщения"""
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_username', 'content', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Сериализатор беседы"""
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'participant1', 'participant2', 'listing',
            'created_at', 'updated_at', 'last_message', 'unread_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

