from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.conversations_list, name='conversations_list'),
    path('conversation/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('start/<int:listing_pk>/', views.conversation_start, name='conversation_start'),
    path('api/messages/<int:conversation_pk>/', views.get_new_messages, name='get_new_messages'),
]

