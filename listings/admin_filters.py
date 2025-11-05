"""
Админка для управления фильтрами категорий
"""
from django.contrib import admin
from .models_filters import CategoryFilter, FilterOption, ListingFilterValue


class FilterOptionInline(admin.TabularInline):
    """Inline для опций фильтра"""
    model = FilterOption
    extra = 3
    fields = ['value', 'display_name', 'order', 'is_active']
    ordering = ['order', 'value']


@admin.register(CategoryFilter)
class CategoryFilterAdmin(admin.ModelAdmin):
    """Админка для фильтров категорий"""
    list_display = ['name', 'category', 'filter_type', 'order', 'is_required', 'is_active']
    list_filter = ['filter_type', 'is_active', 'is_required', 'category__game']
    search_fields = ['name', 'field_name', 'category__name', 'category__game__name']
    ordering = ['category__game', 'category', 'order']
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['category', 'name', 'field_name', 'filter_type']
        }),
        ('Настройки', {
            'fields': ['order', 'is_required', 'is_active']
        }),
    ]
    
    inlines = [FilterOptionInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'category__game')


@admin.register(FilterOption)
class FilterOptionAdmin(admin.ModelAdmin):
    """Админка для опций фильтров"""
    list_display = ['filter', 'value', 'display_name', 'order', 'is_active']
    list_filter = ['is_active', 'filter__category__game']
    search_fields = ['value', 'display_name', 'filter__name']
    ordering = ['filter__category__game', 'filter', 'order']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('filter', 'filter__category', 'filter__category__game')


@admin.register(ListingFilterValue)
class ListingFilterValueAdmin(admin.ModelAdmin):
    """Админка для значений фильтров объявлений"""
    list_display = ['listing', 'category_filter', 'get_value']
    list_filter = ['category_filter__category__game', 'category_filter']
    search_fields = ['listing__title', 'value_text']
    raw_id_fields = ['listing']
    filter_horizontal = ['selected_options']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'listing', 'category_filter', 'category_filter__category', 'category_filter__category__game'
        ).prefetch_related('selected_options')

