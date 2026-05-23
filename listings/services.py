"""
Сервисный слой `listings/`.

Здесь живёт бизнес-логика для объявлений (Listing), категорий, фильтров.
Сервисы должны:
- Принимать keyword-only аргументы.
- Быть type-annotated.
- Использовать `transaction.atomic` + `select_for_update()` для денежных операций
  (например, при изменении цены резервирования).
- Не возвращать HttpResponse.

Naming: `listing_<action>`, например `listing_create`, `listing_archive`.

См. HackSoft styleguide: https://github.com/HackSoftware/Django-Styleguide#services

ВАЖНО: этот файл создан как скелет в рамках P3 рефакторинга.
Постепенно перенесите сюда логику из `listings/views.py` (523 строки).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from accounts.models import CustomUser
    from listings.models import Game, Listing


@transaction.atomic
def listing_create(
    *,
    seller: "CustomUser",
    game: "Game",
    title: str,
    description: str,
    price: Decimal,
    image=None,
) -> "Listing":
    """
    Создание нового объявления.

    Проверяет лимит активных объявлений (settings.MAX_ACTIVE_LISTINGS).
    Если превышен — выбрасывает ValidationError.

    Пример использования (из view):

        from listings.services import listing_create

        def listing_create_view(request):
            form = ListingForm(request.POST, request.FILES)
            if form.is_valid():
                listing = listing_create(
                    seller=request.user,
                    game=form.cleaned_data['game'],
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data['description'],
                    price=form.cleaned_data['price'],
                    image=form.cleaned_data.get('image'),
                )
                messages.success(request, 'Объявление создано')
                return redirect('listings:listing_detail', pk=listing.pk)
            return render(request, 'listings/listing_create.html', {'form': form})
    """
    from django.conf import settings
    from django.core.exceptions import ValidationError

    from listings.models import Listing

    active_count = Listing.objects.filter(seller=seller, status="active").count()
    if active_count >= settings.MAX_ACTIVE_LISTINGS:
        raise ValidationError(
            f"Достигнут лимит активных объявлений ({settings.MAX_ACTIVE_LISTINGS})"
        )

    return Listing.objects.create(
        seller=seller,
        game=game,
        title=title,
        description=description,
        price=price,
        image=image,
        status="active",
    )
