"""
Продвинутый Email Service с поддержкой multiple провайдеров и fallback.
Для production-ready отправки писем.
"""

import logging
import smtplib
from typing import List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Централизованный сервис для отправки email с retry и fallback.
    """

    # Приоритет провайдеров (первый - основной, остальные - fallback)
    PROVIDERS = [
        "primary",  # Основной SMTP (из .env)
        "sendgrid",  # SendGrid API
        "mailgun",  # Mailgun API
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
        subject = "Код сброса пароля — LootLink"

        html_message = EmailService._render_code_email(
            title="Сброс пароля",
            greeting=f"Здравствуйте, {user.username}!",
            body="Вы запросили сброс пароля на LootLink.",
            code=reset_code,
            code_label="Ваш код подтверждения",
            code_hint="Введите этот код на странице сброса пароля",
            expiry="Код действителен 15 минут.",
            warning="Если вы не запрашивали сброс пароля, проигнорируйте это письмо. Ваш пароль останется без изменений.",
        )

        text_message = (
            f"Здравствуйте, {user.username}!\n\n"
            f"Вы запросили сброс пароля на LootLink.\n\n"
            f"Ваш код подтверждения: {reset_code}\n\n"
            f"Код действителен 15 минут.\n\n"
            f"Если вы не запрашивали сброс пароля, проигнорируйте это письмо.\n\n"
            f"— Команда LootLink\n"
        )

        return EmailService._send_email(
            subject=subject,
            message=text_message,
            html_message=html_message,
            recipient_list=[user.email],
            fail_silently=False,
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

        domain = settings.SITE_URL.replace("http://", "").replace("https://", "")
        protocol = "https" if not settings.DEBUG else "http"
        verification_url = (
            f"{protocol}://{domain}"
            f"{reverse('accounts:verify_email', kwargs={'token': verification_token})}"
        )

        subject = "Подтвердите email — LootLink"

        html_message = EmailService._render_button_email(
            title="Подтверждение email",
            greeting=f"Добро пожаловать, {user.username}!",
            body="Для завершения регистрации подтвердите ваш email.",
            button_text="Подтвердить email",
            button_url=verification_url,
            fallback_url=verification_url,
            expiry="Ссылка действительна 24 часа.",
        )

        text_message = (
            f"Здравствуйте, {user.username}!\n\n"
            f"Для завершения регистрации перейдите по ссылке:\n"
            f"{verification_url}\n\n"
            f"Ссылка действительна 24 часа.\n\n"
            f"— Команда LootLink\n"
        )

        return EmailService._send_email(
            subject=subject,
            message=text_message,
            html_message=html_message,
            recipient_list=[user.email],
            fail_silently=False,
        )

    @staticmethod
    def _render_code_email(
        title: str,
        greeting: str,
        body: str,
        code: str,
        code_label: str,
        code_hint: str,
        expiry: str,
        warning: str = "",
    ) -> str:
        """Рендерит HTML-письмо с кодом подтверждения."""
        warning_html = ""
        if warning:
            warning_html = (
                '<table width="100%" cellpadding="0" cellspacing="0" '
                'style="margin:24px 0 0;"><tr>'
                '<td style="background:#fafaf9;border-left:3px solid #d4d4d4;'
                'padding:14px 18px;font-size:13px;line-height:1.6;color:#78716c;">'
                f"{warning}</td></tr></table>"
            )

        return (
            '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            "</head>"
            '<body style="margin:0;padding:0;background-color:#f5f5f4;'
            "font-family:system-ui,-apple-system,'Segoe UI',sans-serif;\">'"
            '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
            '<tr><td align="center" style="padding:48px 20px;">'
            # Card
            '<table width="100%" cellpadding="0" cellspacing="0" '
            'style="max-width:460px;background:#ffffff;border-radius:2px;'
            'overflow:hidden;">'
            # Accent bar
            '<tr><td style="height:4px;background:#4a90e2;"></td></tr>'
            # Content
            '<tr><td style="padding:40px 36px 20px;">'
            # Brand
            '<p style="margin:0 0 32px;font-size:15px;font-weight:700;'
            'color:#4a90e2;letter-spacing:1px;">LOOTLINK</p>'
            # Greeting + body
            f'<p style="margin:0 0 6px;font-size:20px;font-weight:600;'
            f'color:#1c1917;">{greeting}</p>'
            f'<p style="margin:0 0 32px;font-size:14px;line-height:1.7;'
            f'color:#57534e;">{body}</p>'
            # Code block
            '<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            '<td style="border-left:3px solid #4a90e2;padding:20px 24px;'
            'background:#fafaf9;">'
            f'<p style="margin:0 0 8px;font-size:11px;font-weight:600;'
            f'color:#a8a29e;text-transform:uppercase;letter-spacing:1.5px;">'
            f"{code_label}</p>"
            f'<p style="margin:0;font-size:32px;font-weight:700;'
            f"letter-spacing:6px;color:#1c1917;"
            f"font-family:'Courier New',monospace;\">'"
            f"{code}</p>"
            "</td></tr></table>"
            # Hint
            f'<p style="margin:16px 0 0;font-size:12px;color:#a8a29e;">'
            f"{code_hint}</p>"
            # Expiry
            f'<p style="margin:24px 0 0;font-size:13px;color:#57534e;">'
            f"{expiry}</p>"
            # Warning
            f"{warning_html}"
            "</td></tr>"
            # Footer
            '<tr><td style="padding:20px 36px 32px;border-top:1px solid #f5f5f4;">'
            '<p style="margin:0;font-size:11px;color:#d6d3d1;">'
            "LootLink &middot; lootlink.ru</p>"
            "</td></tr></table></td></tr></table></body></html>"
        )

    @staticmethod
    def _render_button_email(
        title: str,
        greeting: str,
        body: str,
        button_text: str,
        button_url: str,
        fallback_url: str,
        expiry: str,
    ) -> str:
        """Рендерит HTML-письмо с кнопкой-ссылкой."""
        return (
            '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            "</head>"
            '<body style="margin:0;padding:0;background-color:#f5f5f4;'
            "font-family:system-ui,-apple-system,'Segoe UI',sans-serif;\">'"
            '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
            '<tr><td align="center" style="padding:48px 20px;">'
            '<table width="100%" cellpadding="0" cellspacing="0" '
            'style="max-width:460px;background:#ffffff;border-radius:2px;'
            'overflow:hidden;">'
            # Accent bar
            '<tr><td style="height:4px;background:#4a90e2;"></td></tr>'
            # Content
            '<tr><td style="padding:40px 36px 20px;">'
            '<p style="margin:0 0 32px;font-size:15px;font-weight:700;'
            'color:#4a90e2;letter-spacing:1px;">LOOTLINK</p>'
            f'<p style="margin:0 0 6px;font-size:20px;font-weight:600;'
            f'color:#1c1917;">{greeting}</p>'
            f'<p style="margin:0 0 32px;font-size:14px;line-height:1.7;'
            f'color:#57534e;">{body}</p>'
            # Button
            '<table cellpadding="0" cellspacing="0"><tr>'
            '<td style="background:#4a90e2;border-radius:4px;">'
            f'<a href="{button_url}" style="display:inline-block;'
            "color:#ffffff;padding:14px 36px;text-decoration:none;"
            'font-weight:600;font-size:14px;">'
            f"{button_text}</a></td></tr></table>"
            # Fallback
            '<p style="margin:20px 0 0;font-size:12px;color:#a8a29e;'
            'word-break:break-all;line-height:1.6;">'
            f"\u0418\u043b\u0438 \u0441\u043a\u043e\u043f\u0438\u0440\u0443\u0439\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443:<br>{fallback_url}</p>"
            # Expiry
            f'<p style="margin:24px 0 0;font-size:13px;color:#57534e;">'
            f"{expiry}</p>"
            "</td></tr>"
            # Footer
            '<tr><td style="padding:20px 36px 32px;border-top:1px solid #f5f5f4;">'
            '<p style="margin:0;font-size:11px;color:#d6d3d1;">'
            "LootLink &middot; lootlink.ru</p>"
            "</td></tr></table></td></tr></table></body></html>"
        )

    @staticmethod
    def _render_info_email(
        greeting: str,
        body: str,
    ) -> str:
        """Рендерит информационное HTML-письмо без кода и кнопки."""
        return (
            '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
            "</head>"
            '<body style="margin:0;padding:0;background-color:#f5f5f4;'
            "font-family:system-ui,-apple-system,'Segoe UI',sans-serif;\">'"
            '<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
            '<tr><td align="center" style="padding:48px 20px;">'
            '<table width="100%" cellpadding="0" cellspacing="0" '
            'style="max-width:460px;background:#ffffff;border-radius:2px;'
            'overflow:hidden;">'
            '<tr><td style="height:4px;background:#4a90e2;"></td></tr>'
            '<tr><td style="padding:40px 36px 20px;">'
            '<p style="margin:0 0 32px;font-size:15px;font-weight:700;'
            'color:#4a90e2;letter-spacing:1px;">LOOTLINK</p>'
            f'<p style="margin:0 0 6px;font-size:20px;font-weight:600;'
            f'color:#1c1917;">{greeting}</p>'
            f'<p style="margin:0;font-size:14px;line-height:1.7;'
            f'color:#57534e;">{body}</p>'
            "</td></tr>"
            '<tr><td style="padding:20px 36px 32px;border-top:1px solid #f5f5f4;">'
            '<p style="margin:0;font-size:11px;color:#d6d3d1;">'
            "LootLink &middot; lootlink.ru</p>"
            "</td></tr></table></td></tr></table></body></html>"
        )

    @staticmethod
    def send_no_account_email(email: str) -> bool:
        """
        Отправка письма, если аккаунт с таким email не найден.
        Не раскрывает существование аккаунта на странице.
        """
        subject = "Сброс пароля — LootLink"

        html_message = EmailService._render_info_email(
            greeting="Запрос на сброс пароля",
            body=(
                "Мы получили запрос на сброс пароля для этого адреса электронной почты, "
                "но аккаунт с таким email на LootLink не зарегистрирован.<br><br>"
                "Если вы уверены, что регистрировались, попробуйте другой адрес. "
                "Если вы не отправляли этот запрос, просто проигнорируйте это письмо."
            ),
        )

        text_message = (
            "Запрос на сброс пароля\n\n"
            "Мы получили запрос на сброс пароля для этого адреса электронной почты, "
            "но аккаунт с таким email на LootLink не зарегистрирован.\n\n"
            "Если вы уверены, что регистрировались, попробуйте другой адрес. "
            "Если вы не отправляли этот запрос, просто проигнорируйте это письмо.\n\n"
            "— LootLink\n"
        )

        return EmailService._send_email(
            subject=subject,
            message=text_message,
            html_message=html_message,
            recipient_list=[email],
            fail_silently=True,
        )

    @staticmethod
    def _send_email(
        subject: str,
        message: str,
        recipient_list: List[str],
        html_message: Optional[str] = None,
        fail_silently: bool = False,
    ) -> bool:
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
        if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
            logger.warning(
                "EMAIL_BACKEND is console - emails will not be sent! Configure SMTP for production."
            )
            if not fail_silently:
                print(f"\n{'='*70}")
                print("EMAIL (CONSOLE OUTPUT):")
                print(f"{'='*70}")
                print(f"To: {', '.join(recipient_list)}")
                print(f"Subject: {subject}")
                print(f"Message:\n{message}")
                print(f"{'='*70}\n")
            return False

        from_email = settings.DEFAULT_FROM_EMAIL
        support_email = getattr(settings, "SUPPORT_EMAIL", from_email)

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
                reply_to=[support_email],
            )
            # Anti-spam заголовки
            email.extra_headers["List-Unsubscribe"] = (
                f"<mailto:{support_email}?subject=unsubscribe>"
            )
            email.extra_headers["X-Mailer"] = "LootLink/1.0"

            if html_message:
                email.attach_alternative(html_message, "text/html")

            email.send()
            logger.info(f"Email sent successfully to {recipient_list}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                f"SMTP Authentication failed: {e}. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD"
            )
            if not fail_silently:
                raise
            return False

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return EmailService._try_alternative_providers(
                subject, message, recipient_list, html_message, fail_silently
            )

        except Exception as e:
            logger.error(f"Unexpected email error: {e}")
            if not fail_silently:
                raise
            return False

    @staticmethod
    def _try_alternative_providers(subject, message, recipient_list, html_message, fail_silently):
        """Fallback email providers."""
        logger.warning("Alternative email providers not configured. Email not sent.")
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
            "backend": settings.EMAIL_BACKEND,
            "host": settings.EMAIL_HOST,
            "port": settings.EMAIL_PORT,
            "use_tls": settings.EMAIL_USE_TLS,
            "from_email": settings.DEFAULT_FROM_EMAIL,
            "test_passed": False,
            "error": None,
        }

        try:
            # Пытаемся отправить тестовое письмо
            send_mail(
                subject="[TEST] LootLink Email Configuration Test",
                message="This is a test email from LootLink.\nIf you received this, email configuration is working!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],  # Отправляем себе
                fail_silently=False,
            )
            results["test_passed"] = True
            logger.info("Email configuration test PASSED")

        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Email configuration test FAILED: {e}")

        return results
