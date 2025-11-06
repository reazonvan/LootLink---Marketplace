"""
REST API URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from . import views

app_name = 'api'

router = DefaultRouter()
router.register(r'games', views.GameViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'listings', views.ListingViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'conversations', views.ConversationViewSet, basename='conversation')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
]

