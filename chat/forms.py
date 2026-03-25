from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    """
    Форма отправки сообщения.
    """
    class Meta:
        model = Message
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите сообщение...'
            })
        }
        labels = {
            'content': '',
            'image': '',
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content', '').strip()
        image = cleaned_data.get('image')
        if not content and not image:
            raise forms.ValidationError('Введите сообщение или прикрепите изображение.')
        return cleaned_data

