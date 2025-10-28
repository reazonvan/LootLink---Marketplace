from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender', 'content', 'created_at', 'is_read']
    can_delete = False
    max_num = 10


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['get_participants', 'listing', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['participant1__username', 'participant2__username', 'listing__title']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [MessageInline]
    
    def get_participants(self, obj):
        return f"{obj.participant1.username} ↔ {obj.participant2.username}"
    get_participants.short_description = 'Участники'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'sender', 'content_preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'content']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Сообщение'

