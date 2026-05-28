from django import forms

from .models import PurchaseRequest, Review


class PurchaseRequestForm(forms.ModelForm):
    """
    Форма создания запроса на покупку.
    """

    class Meta:
        model = PurchaseRequest
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Напишите сообщение продавцу (необязательно)...",
                }
            )
        }
        labels = {"message": "Сообщение продавцу"}


class ReviewForm(forms.ModelForm):
    """
    Форма создания отзыва.
    """

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(
                choices=[
                    (1, "1 — плохо"),
                    (2, "2 — слабо"),
                    (3, "3 — нормально"),
                    (4, "4 — хорошо"),
                    (5, "5 — отлично"),
                ]
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Поделитесь своим опытом сделки...",
                }
            ),
        }
        labels = {"rating": "Оценка", "comment": "Комментарий"}
