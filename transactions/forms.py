from django import forms
from .models import PurchaseRequest, Review


class PurchaseRequestForm(forms.ModelForm):
    """
    Форма создания запроса на покупку.
    """
    class Meta:
        model = PurchaseRequest
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Напишите сообщение продавцу (необязательно)...'
            })
        }
        labels = {
            'message': 'Сообщение продавцу'
        }


class ReviewForm(forms.ModelForm):
    """
    Форма создания отзыва.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, f'{i} ★') for i in range(1, 6)]
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Поделитесь своим опытом сделки...'
            })
        }
        labels = {
            'rating': 'Оценка',
            'comment': 'Комментарий'
        }

