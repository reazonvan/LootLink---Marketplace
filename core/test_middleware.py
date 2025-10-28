"""
Comprehensive тесты для middleware.
"""
import pytest
from django.test import RequestFactory
from django.http import HttpResponse
from core.middleware import SimpleRateLimitMiddleware, SecurityHeadersMiddleware
from django.contrib.auth import get_user_model
from django.core.cache import cache

CustomUser = get_user_model()


@pytest.mark.django_db
class TestSimpleRateLimitMiddleware:
    """Тесты rate limiting middleware."""
    
    def setup_method(self):
        """Очистка кеша перед каждым тестом."""
        cache.clear()
    
    def test_get_request_not_limited(self):
        """GET запросы не лимитируются."""
        factory = RequestFactory()
        request = factory.get('/some/path/')
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SimpleRateLimitMiddleware(get_response)
        response = middleware(request)
        
        assert response.status_code == 200
    
    def test_post_request_within_limit(self):
        """POST запрос в пределах лимита."""
        factory = RequestFactory()
        request = factory.post('/accounts/login/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SimpleRateLimitMiddleware(get_response)
        response = middleware(request)
        
        assert response.status_code == 200
    
    def test_post_request_exceeds_limit(self):
        """POST запрос превышает лимит."""
        factory = RequestFactory()
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SimpleRateLimitMiddleware(get_response)
        
        # Делаем 6 запросов (лимит 5 для /accounts/login/)
        for i in range(6):
            request = factory.post('/accounts/login/')
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            response = middleware(request)
        
        # Последний запрос должен быть заблокирован
        assert response.status_code == 403
        assert 'Слишком много попыток' in response.content.decode()
    
    def test_different_ips_not_affected(self):
        """Разные IP не влияют друг на друга."""
        factory = RequestFactory()
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SimpleRateLimitMiddleware(get_response)
        
        # IP 1 делает 5 запросов
        for i in range(5):
            request = factory.post('/accounts/login/')
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            response = middleware(request)
            assert response.status_code == 200
        
        # IP 2 может сделать свои запросы
        request = factory.post('/accounts/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        response = middleware(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestSecurityHeadersMiddleware:
    """Тесты security headers middleware."""
    
    def test_security_headers_added(self, settings):
        """Security headers добавляются."""
        settings.DEBUG = False
        
        factory = RequestFactory()
        request = factory.get('/')
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SecurityHeadersMiddleware(get_response)
        response = middleware(request)
        
        # Проверяем основные заголовки
        assert 'X-Content-Type-Options' in response
        assert response['X-Content-Type-Options'] == 'nosniff'
        
        assert 'X-Frame-Options' in response
        assert response['X-Frame-Options'] == 'DENY'
        
        assert 'X-XSS-Protection' in response
        assert response['X-XSS-Protection'] == '1; mode=block'
        
        assert 'Referrer-Policy' in response
        assert 'Permissions-Policy' in response
    
    def test_csp_header_production(self, settings):
        """CSP header в production."""
        settings.DEBUG = False
        
        factory = RequestFactory()
        request = factory.get('/')
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SecurityHeadersMiddleware(get_response)
        response = middleware(request)
        
        assert 'Content-Security-Policy' in response
        # В production CSP строже
        assert 'unsafe-eval' not in response['Content-Security-Policy']
    
    def test_csp_header_development(self, settings):
        """CSP header в development."""
        settings.DEBUG = True
        
        factory = RequestFactory()
        request = factory.get('/')
        
        def get_response(request):
            return HttpResponse("OK")
        
        middleware = SecurityHeadersMiddleware(get_response)
        response = middleware(request)
        
        assert 'Content-Security-Policy' in response
        # В development CSP мягче
        csp = response['Content-Security-Policy']
        assert 'unsafe-inline' in csp or 'unsafe-eval' in csp

