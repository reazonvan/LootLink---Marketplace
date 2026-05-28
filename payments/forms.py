import logging
from decimal import Decimal

from django import forms

from .models import PromoCode, Withdrawal

logger = logging.getLogger(__name__)


class DepositForm(forms.Form):
    """Форма пополнения баланса"""

    AMOUNT_CHOICES = [
        (100, "100 ₽"),
        (500, "500 ₽"),
        (1000, "1000 ₽"),
        (2000, "2000 ₽"),
        (5000, "5000 ₽"),
    ]

    amount = forms.ChoiceField(
        choices=AMOUNT_CHOICES, widget=forms.RadioSelect, label="Выберите сумму", required=False
    )
    custom_amount = forms.DecimalField(
        min_value=10,
        max_value=100000,
        decimal_places=2,
        required=False,
        label="Или введите свою сумму",
        help_text="От 10 до 100000 ₽",
    )

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        custom_amount = cleaned_data.get("custom_amount")

        if not amount and not custom_amount:
            raise forms.ValidationError("Выберите сумму или введите свою")

        if custom_amount:
            cleaned_data["final_amount"] = custom_amount
        else:
            cleaned_data["final_amount"] = Decimal(amount)

        return cleaned_data


class PromoCodeForm(forms.Form):
    """Форма применения промокода"""

    code = forms.CharField(
        max_length=50,
        label="Промокод",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите промокод"}),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        try:
            promo = PromoCode.objects.get(code=code)
            if not promo.is_valid():
                logger.info("promo code expired/invalid: code=%s", code)
                raise forms.ValidationError("Промокод недействителен или истек")
            self.promo_code = promo
            return code
        except PromoCode.DoesNotExist:
            logger.info("promo code not found: code=%s", code)
            raise forms.ValidationError("Промокод не найден")


class WithdrawalForm(forms.Form):
    """Форма заявки на вывод средств.

    P0-4: не ModelForm — иначе form.save() пишет payment_details в БД
    в открытом виде, минуя set_payment_details() с шифрованием.
    Сохранение делает сервис create_withdrawal(...).
    """

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=100,
        label="Сумма",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "Минимум 100 ₽",
                "min": "100",
            }
        ),
    )
    payment_method = forms.ChoiceField(
        choices=Withdrawal.PAYMENT_METHODS,
        label="Способ вывода",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    payment_details = forms.CharField(
        max_length=255,
        label="Реквизиты",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Номер карты, кошелька и т.д.",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < 100:
            raise forms.ValidationError("Минимальная сумма вывода 100 ₽")

        if self.user:
            try:
                wallet = self.user.wallet
                available = wallet.get_available_balance()
                if amount > available:
                    logger.info(
                        "withdrawal denied (insufficient funds): user=%s amount=%s available=%s",
                        self.user.pk,
                        amount,
                        available,
                    )
                    raise forms.ValidationError(f"Недостаточно средств. Доступно: {available} ₽")
            except Withdrawal._meta.model.user.field.related_model.wallet.RelatedObjectDoesNotExist:
                logger.warning(
                    "withdrawal denied (no wallet): user=%s amount=%s",
                    self.user.pk,
                    amount,
                )
                raise forms.ValidationError("У вас нет кошелька. Пополните баланс.")
        return amount

    def clean_payment_details(self):
        """Базовая валидация реквизитов до шифрования."""
        details = (self.cleaned_data.get("payment_details") or "").strip()
        if not details:
            raise forms.ValidationError("Введите реквизиты.")
        if len(details) < 4:
            raise forms.ValidationError("Реквизиты слишком короткие.")
        return details
