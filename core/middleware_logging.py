"""
Middleware для request_id — уникальный идентификатор каждого HTTP-запроса.
Позволяет связывать все логи одного запроса между собой.
"""
import logging
import threading
import uuid

_request_id = threading.local()


def get_request_id():
    return getattr(_request_id, 'id', '-')


class RequestIDFilter(logging.Filter):
    """Добавляет request_id в каждую запись лога."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True


class RequestIDMiddleware:
    """
    Генерирует UUID для каждого запроса, сохраняет в thread-local
    и пробрасывает в заголовок ответа X-Request-ID.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex[:12])
        _request_id.id = rid
        request.request_id = rid

        response = self.get_response(request)
        response['X-Request-ID'] = rid

        _request_id.id = None
        return response
