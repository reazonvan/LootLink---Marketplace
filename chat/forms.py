from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError

from core.validators import SecureImageValidator

from .models import Message


class MessageForm(forms.ModelForm):
    """
    Форма отправки сообщения. P1-22: валидация прикрепляемого изображения.
    """

    class Meta:
        model = Message
        fields = ["content", "image"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Введите сообщение...",
                    "maxlength": "5000",
                }
            )
        }
        labels = {
            "content": "",
            "image": "",
        }

    def clean_content(self):
        content = (self.cleaned_data.get("content") or "").strip()
        if len(content) > 5000:
            raise forms.ValidationError("Сообщение не должно превышать 5000 символов.")
        return content

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            try:
                SecureImageValidator(max_size_mb=5)(image)
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return image

    def clean(self):
        cleaned_data = super().clean()
        content = (cleaned_data.get("content") or "").strip()
        image = cleaned_data.get("image")
        if not content and not image:
            raise forms.ValidationError("Введите сообщение или прикрепите изображение.")
        return cleaned_data
