"""
Формы для системы жалоб.
"""
from django import forms
from .models import Report


class ReportForm(forms.ModelForm):
    """Форма подачи жалобы."""
    
    class Meta:
        model = Report
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробно опишите проблему...',
                'required': True,
                'maxlength': '1000'
            })
        }
        labels = {
            'reason': 'Причина жалобы',
            'description': 'Описание'
        }
        help_texts = {
            'description': 'Максимум 1000 символов. Опишите проблему как можно подробнее.'
        }
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if len(description) < 20:
            raise forms.ValidationError('Описание должно содержать минимум 20 символов.')
        return description
