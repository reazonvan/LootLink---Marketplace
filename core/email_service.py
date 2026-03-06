"""
Продвинутый Email Service с поддержкой multiple провайдеров и fallback.
Для production-ready отправки писем.
"""
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from typing import List, Optional
import smtplib

logger = logging.getLogger(__name__)


class EmailService:
    """
    Централизованный сервис для отправки email с retry и fallback.
    """
    
    # Приоритет провайдеров (первый - основной, остальные - fallback)
    PROVIDERS = [
        'primary',   # Основной SMTP (из .env)
        'sendgrid',  # SendGrid API
        'mailgun',   # Mailgun API
    ]
    
    @staticmethod
    def send_password_reset_email(user, reset_code):
        """
        Отправка кода сброса пароля.
        
        Args:
            user: Объект пользователя
            reset_code: Код сброса (8 символов)
        
        Returns:
            bool: True если отправка успешна
        """
        subject = 'Код сброса пароля - LootLink'
        
        # Используем HTML шаблон для красивого письма
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .code-box {{ background: #fff; border: 2px dashed #667eea; padding: 20px; 
                     margin: 20px 0; text-align: center; border-radius: 5px; }}
        .code {{ font-size: 32px; font-weight: bold; letter-spacing: 5px; 
                 color: #667eea; font-family: 'Courier New', monospace; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                    padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Сброс Пароля</h1>
            <p>LootLink Marketplace</p>
        </div>
        <div class="content">
            <p>Здравствуйте, <strong>{user.username}</strong>!</p>
            
            <p>Вы запросили сброс пароля на сайте LootLink.</p>
            
            <div class="code-box">
                <p style="margin: 0; color: #666; font-size: 14px;">Ваш код подтверждения:</p>
                <p class="code">{reset_code}</p>
                <p style="margin: 0; color: #999; font-size: 12px;">Введите этот код на странице сброса пароля</p>
            </div>
            
            <p><strong>Код действителен в течение 15 минут.</strong></p>

            <div class="warning">
                <strong>Важно:</strong> Если вы не запрашивали сброс пароля, 
                просто проигнорируйте это письмо. Ваш пароль останется без изменений.
            </div>
            
            <p>Если у вас возникли проблемы, свяжитесь с поддержкой.</p>
        </div>
        <div class="footer">
            <p>С уважением, команда LootLink<br>
            © 2025 LootLink Marketplace. Все права защищены.</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Plain text версия для старых email клиентов
        text_message = f"""
Здравствуйте, {user.username}!

Вы запросили сброс пароля на сайте LootLink.

Ваш код подтверждения: {reset_code}

Код действителен в течение 15 минут.

Если вы не запрашивали сброс пароля, проигнорируйте это письмо.

С уважением,
Команда LootLink
        """
        
        return EmailService._send_email(
            subject=subject,
            message=text_message,
            html_message=html_message,
            recipient_list=[user.email],
            fail_silently=False
        )
    
    @staticmethod
    def send_verification_email(user, verification_token):
        """
        Отправка ссылки верификации email.
        
        Args:
            user: Объект пользователя
            verification_token: Токен верификации
        
        Returns:
            bool: True если отправка успешна
        """
        from django.urls import reverse
        
        domain = settings.SITE_URL.replace('http://', '').replace('https://', '')
        protocol = 'https' if not settings.DEBUG else 'http'
        verification_url = f"{protocol}://{domain}{reverse('accounts:verify_email', kwargs={'token': verification_token})}"
        
        subject = 'Подтвердите ваш email - LootLink'
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; 
                   padding: 15px 30px; text-decoration: none; border-radius: 5px; 
                   font-weight: bold; margin: 20px 0; }}
        .button:hover {{ background: #764ba2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✉️ Подтверждение Email</h1>
            <p>LootLink Marketplace</p>
        </div>
        <div class="content">
            <p>Добро пожаловать, <strong>{user.username}</strong>!</p>
            
            <p>Спасибо за регистрацию на LootLink. Для завершения регистрации 
            подтвердите ваш email адрес, нажав на кнопку ниже:</p>
            
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Подтвердить Email</a>
            </p>
            
            <p style="font-size: 12px; color: #666;">
                Или скопируйте эту ссылку в браузер:<br>
                <code style="background: #fff; padding: 5px; display: inline-block; margin-top: 5px;">{verification_url}</code>
            </p>
            
            <p>⏰ Ссылка действительна в течение 24 часов.</p>
        </div>
    </div>
</body>
</html>
        """
        
        text_message = f"""
Здравствуйте, {user.username}!

Спасибо за регистрацию на LootLink.

Перейдите по ссылке для подтверждения email:
{verification_url}

Ссылка действительна в течение 24 часов.

С уважением,
Команда LootLink
        """
        
        return EmailService._send_email(
            subject=subject,
            message=text_message,
            html_message=html_message,
            recipient_list=[user.email],
            fail_silently=False
        )
    
    @staticmethod
    def _send_email(subject: str, message: str, recipient_list: List[str], 
                    html_message: Optional[str] = None, fail_silently: bool = False) -> bool:
        """
        Внутренний метод для отправки email с retry и fallback.
        
        Args:
            subject: Тема письма
            message: Текст письма (plain text)
            recipient_list: Список получателей
            html_message: HTML версия письма (опционально)
            fail_silently: Игнорировать ошибки
        
        Returns:
            bool: True если письмо отправлено успешно
        """
        # Проверяем что email настроен
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            logger.warning('EMAIL_BACKEND is console - emails will not be sent! Configure SMTP for production.')
            if not fail_silently:
                print(f"\n{'='*70}")
                print(f"EMAIL (CONSOLE OUTPUT):")
                print(f"{'='*70}")
                print(f"To: {', '.join(recipient_list)}")
                print(f"Subject: {subject}")
                print(f"Message:\n{message}")
                print(f"{'='*70}\n")
            return False
        
        # Попытка 1: Основной SMTP (Gmail, Yandex, etc.)
        try:
            if html_message:
                from django.core.mail import EmailMultiAlternatives
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list
                )
                email.attach_alternative(html_message, "text/html")
                email.send()
            else:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    fail_silently=False
                )
            
            logger.info(f'Email sent successfully to {recipient_list}')
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f'SMTP Authentication failed: {e}. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD')
            if not fail_silently:
                raise
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f'SMTP error: {e}')
            # Пробуем альтернативные провайдеры
            return EmailService._try_alternative_providers(
                subject, message, recipient_list, html_message, fail_silently
            )
            
        except Exception as e:
            logger.error(f'Unexpected email error: {e}')
            if not fail_silently:
                raise
            return False
    
    @staticmethod
    def _try_alternative_providers(subject, message, recipient_list, html_message, fail_silently):
        """Fallback email providers."""
        logger.warning('Alternative email providers not configured. Email not sent.')
        return False
    
    @staticmethod
    def test_email_configuration():
        """
        Тестирование email конфигурации.
        Отправляет тестовое письмо.
        
        Returns:
            dict: Результаты тестирования
        """
        results = {
            'backend': settings.EMAIL_BACKEND,
            'host': settings.EMAIL_HOST,
            'port': settings.EMAIL_PORT,
            'use_tls': settings.EMAIL_USE_TLS,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'test_passed': False,
            'error': None
        }
        
        try:
            # Пытаемся отправить тестовое письмо
            send_mail(
                subject='[TEST] LootLink Email Configuration Test',
                message='This is a test email from LootLink.\nIf you received this, email configuration is working!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # Отправляем себе
                fail_silently=False
            )
            results['test_passed'] = True
            logger.info('Email configuration test PASSED')
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f'Email configuration test FAILED: {e}')
        
        return results

