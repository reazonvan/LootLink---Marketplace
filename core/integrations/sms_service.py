# -*- coding: utf-8 -*-
"""
Сервис для отправки SMS через SMS.ru
Документация API: https://sms.ru/api
"""

import logging

from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class SMSService:
    """Сервис для отправки СМС через SMS.ru"""

    def __init__(self):
        self.api_id = getattr(settings, "SMS_RU_API_KEY", None)
        self.api_url = "https://sms.ru/sms/send"
        self.enabled = getattr(settings, "SMS_ENABLED", False)

    def send_sms(self, phone, message):
        """
        Отправляет СМС на указанный номер.

        Args:
            phone (str): Номер телефона в формате +79991234567
            message (str): Текст сообщения

        Returns:
            bool: True если отправлено успешно, False если ошибка
        """
        if not self.enabled:
            logger.info("SMS отключены. Сообщение для %s: %s", phone, message)
            return True

        if not self.api_id:
            logger.error("SMS_RU_API_KEY не настроен! Сообщение для %s: %s", phone, message)
            return False

        try:
            # Очищаем номер от лишних символов
            clean_phone = "".join(filter(str.isdigit, phone))

            # Формируем запрос к API SMS.ru
            params = {
                "api_id": self.api_id,
                "to": clean_phone,
                "msg": message,
                "json": 1,  # Ответ в JSON формате
            }

            response = requests.get(self.api_url, params=params, timeout=10)
            data = response.json()

            # Проверяем статус
            if data.get("status") == "OK":
                logger.info(f"SMS успешно отправлено на {phone}")
                return True
            else:
                error_code = data.get("status_code")
                error_text = data.get("status_text", "Unknown error")
                logger.error(f"Ошибка отправки SMS: {error_code} - {error_text}")
                return False

        except Exception as e:
            logger.error("Исключение при отправке SMS на %s: %s — сообщение: %s", phone, e, message)
            return False

    def send_verification_code(self, phone, code):
        """Отправляет код верификации на телефон."""
        message = f"LootLink: Ваш код подтверждения: {code}\n\nКод действителен 15 минут."
        return self.send_sms(phone, message)

    def send_password_reset_code(self, phone, code, username):
        """Отправляет код сброса пароля на телефон."""
        message = f"LootLink: Код для сброса пароля ({username}): {code}\n\nДействителен 15 минут."
        return self.send_sms(phone, message)


# Singleton instance
sms_service = SMSService()


def send_sms(phone, message):
    """Удобная функция для отправки СМС."""
    return sms_service.send_sms(phone, message)


def send_verification_sms(phone, code):
    """Отправляет код верификации."""
    return sms_service.send_verification_code(phone, code)


def send_password_reset_sms(phone, code, username):
    """Отправляет код сброса пароля."""
    return sms_service.send_password_reset_code(phone, code, username)
