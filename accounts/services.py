"""
Сервисный слой `accounts/`.

Здесь живёт бизнес-логика, связанная с пользователями и профилями.
Сервисы должны:
- Принимать keyword-only аргументы (def user_create(*, username, email, password)).
- Быть type-annotated.
- Использовать `transaction.atomic` для атомарных операций.
- Не возвращать HttpResponse — это работа views.

Naming: `<entity>_<action>`, например `user_register`, `profile_update`.

См. HackSoft styleguide: https://github.com/HackSoftware/Django-Styleguide#services

ВАЖНО: этот файл создан как скелет в рамках P3 рефакторинга.
Постепенно перенесите сюда логику из `accounts/views.py` (640 строк),
оставляя во views только: валидация формы → вызов сервиса → redirect/render.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction

CustomUser = get_user_model()
logger = logging.getLogger(__name__)


@transaction.atomic
def user_register(*, username: str, email: str, password: str, phone: str = "") -> "CustomUser":
    """
    Регистрация нового пользователя.

    Создаёт CustomUser, сразу через сигнал создаётся Profile.
    Если передан phone — сохраняем в profile.phone.

    Возвращает созданного пользователя.

    Пример использования (из view):

        from accounts.services import user_register

        def register(request):
            form = RegisterForm(request.POST)
            if form.is_valid():
                user = user_register(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1'],
                    phone=form.cleaned_data.get('phone', ''),
                )
                login(request, user)
                return redirect('listings:catalog')
            return render(request, 'accounts/register.html', {'form': form})
    """
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
    )
    if phone:
        # Profile создаётся сигналом post_save
        user.profile.phone = phone
        user.profile.save()
    logger.info(
        "user registered: id=%s username=%r email=%r phone_set=%s",
        user.pk,
        username,
        email,
        bool(phone),
    )
    return user
