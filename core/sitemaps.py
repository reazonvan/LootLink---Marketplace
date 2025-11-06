"""
Sitemaps для SEO.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from listings.models import Listing, Game
from accounts.models import CustomUser


class StaticViewSitemap(Sitemap):
    """Статические страницы"""
    priority = 0.5
    changefreq = 'weekly'
    
    def items(self):
        return ['listings:home', 'listings:catalog', 'about', 'rules']
    
    def location(self, item):
        return reverse(item)


class GameSitemap(Sitemap):
    """Игры"""
    changefreq = 'daily'
    priority = 0.8
    
    def items(self):
        return Game.objects.filter(is_active=True)
    
    def lastmod(self, obj):
        return obj.created_at
    
    def location(self, obj):
        return reverse('listings:game_listings', args=[obj.slug])


class ListingSitemap(Sitemap):
    """Объявления"""
    changefreq = 'hourly'
    priority = 1.0
    
    def items(self):
        return Listing.objects.filter(status='active').select_related('game')
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return reverse('listings:listing_detail', args=[obj.pk])


class ProfileSitemap(Sitemap):
    """Профили пользователей"""
    changefreq = 'weekly'
    priority = 0.6
    
    def items(self):
        return CustomUser.objects.filter(is_active=True, profile__is_verified=True)
    
    def lastmod(self, obj):
        return obj.profile.updated_at if hasattr(obj, 'profile') else obj.date_joined
    
    def location(self, obj):
        return reverse('accounts:profile', args=[obj.username])


sitemaps = {
    'static': StaticViewSitemap,
    'games': GameSitemap,
    'listings': ListingSitemap,
    'profiles': ProfileSitemap,
}

