"""
Middleware для автоматического аудита безопасности.
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from .models_audit import SecurityAuditLog
import logging

logger = logging.getLogger('django.security')


class BruteForceProtectionMiddleware(MiddlewareMixin):
    """
    Защита от брутфорс атак на основе количества неудачных попыток входа.
    """
    
    MAX_FAILED_ATTEMPTS = 10  # Максимум попыток за период
    LOCKOUT_MINUTES = 30  # Время блокировки
    
    def process_request(self, request):
        """Проверяем количество неудачных попыток входа с IP."""
        
        # Проверяем только страницы входа
        if request.path in ['/accounts/login/', '/api/auth/login/']:
            ip_address = self._get_client_ip(request)
            
            # Проверяем количество неудачных попыток
            failed_attempts = SecurityAuditLog.get_failed_login_attempts(
                ip_address=ip_address,
                minutes=self.LOCKOUT_MINUTES
            )
            
            if failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                SecurityAuditLog.log(
                    action_type='suspicious_activity',
                    description=f'IP заблокирован за превышение попыток входа: {ip_address}',
                    risk_level='critical',
                    ip_address=ip_address,
                    metadata={
                        'failed_attempts': failed_attempts,
                        'lockout_minutes': self.LOCKOUT_MINUTES
                    }
                )
                
                logger.error(f'Brute force attempt blocked from IP: {ip_address}')
                
                return HttpResponseForbidden(
                    '🚫 Слишком много неудачных попыток входа. '
                    f'Попробуйте снова через {self.LOCKOUT_MINUTES} минут.'
                )
        
        return None
    
    @staticmethod
    def _get_client_ip(request):
        from core.utils import get_client_ip
        return get_client_ip(request)


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Middleware для логирования подозрительных действий и security events.
    """
    
    def process_response(self, request, response):
        """Логируем подозрительные response коды."""
        
        # 403 - попытка доступа к запрещенному ресурсу (возможная IDOR атака)
        if response.status_code == 403 and request.user.is_authenticated:
            SecurityAuditLog.log(
                action_type='idor_attempt',
                user=request.user,
                description=f'Попытка доступа к запрещенному ресурсу: {request.path}',
                risk_level='high',
                request=request,
                metadata={
                    'path': request.path,
                    'method': request.method,
                    'status_code': 403
                }
            )
            logger.warning(f'IDOR attempt by {request.user.username} on {request.path}')
        
        return response
    
    def process_exception(self, request, exception):
        """Логируем критичные ошибки."""
        
        # Логируем только для аутентифицированных пользователей
        if request.user.is_authenticated:
            SecurityAuditLog.log(
                action_type='suspicious_activity',
                user=request.user,
                description=f'Exception: {type(exception).__name__}: {str(exception)}',
                risk_level='medium',
                request=request,
                metadata={
                    'exception_type': type(exception).__name__,
                    'exception_message': str(exception),
                    'path': request.path
                }
            )
        
        return None  # Не обрабатываем exception, передаем дальше


# Signal handlers для логирования событий аутентификации
@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Логируем неудачные попытки входа."""
    username = credentials.get('username', 'unknown')
    
    # Получаем IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    SecurityAuditLog.log(
        action_type='login_failed',
        description=f'Неудачная попытка входа: {username}',
        risk_level='medium',
        request=request,
        metadata={
            'username': username,
            'ip_address': ip_address
        }
    )
    
    logger.warning(f'Failed login attempt for user: {username} from IP: {ip_address}')
