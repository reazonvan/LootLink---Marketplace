"""
URL configuration for LootLink project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Favicon redirect (to avoid 404)
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.svg', permanent=True)),
    path('', include('listings.urls')),
    path('accounts/', include('accounts.urls')),
    path('transactions/', include('transactions.urls')),
    path('chat/', include('chat.urls')),
    path('', include('core.urls')),
    path('about/', core_views.about, name='about'),
    path('rules/', core_views.rules, name='rules'),
]

# Custom error handlers
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'

# Serve media files in development
if not settings.USE_S3 and settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

