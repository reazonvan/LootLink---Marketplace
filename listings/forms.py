from django import forms
from .models import Listing, Game, Category


class ListingCreateForm(forms.ModelForm):
    """
    Форма создания нового объявления с категорией.
    """
    class Meta:
        model = Listing
        fields = ['game', 'category', 'title', 'description', 'price', 'image']
        widgets = {
            'game': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_game'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Легендарный меч огня'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Подробно опишите предмет, его характеристики и условия передачи...',
                'maxlength': '5000'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'game': 'Игра',
            'category': 'Категория',
            'title': 'Название предмета',
            'description': 'Описание',
            'price': 'Цена (₽)',
            'image': 'Изображение (необязательно)'
        }
        help_texts = {
            'category': 'Выберите категорию товара (появится после выбора игры)',
            'image': 'Вы можете добавить изображение предмета (необязательно)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только активные игры
        self.fields['game'].queryset = Game.objects.filter(is_active=True)
        # Категория необязательна
        self.fields['category'].required = False
        # Изображение необязательно
        self.fields['image'].required = False
        self.fields['image'].widget.is_required = False
        
        # Если редактируем объявление и есть игра, показываем категории этой игры
        if self.instance.pk and self.instance.game:
            self.fields['category'].queryset = Category.objects.filter(
                game=self.instance.game,
                is_active=True
            )
        elif 'game' in self.data:
            try:
                game_id = int(self.data.get('game'))
                self.fields['category'].queryset = Category.objects.filter(
                    game_id=game_id,
                    is_active=True
                )
            except (ValueError, TypeError):
                self.fields['category'].queryset = Category.objects.none()
        else:
            self.fields['category'].queryset = Category.objects.none()


class ListingUpdateForm(forms.ModelForm):
    """
    Форма редактирования объявления.
    """
    class Meta:
        model = Listing
        fields = ['game', 'category', 'title', 'description', 'price', 'image', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'status': forms.Select(attrs={'class': 'form-select'})
        }
        labels = {
            'title': 'Название предмета',
            'description': 'Описание',
            'price': 'Цена (₽)',
            'image': 'Изображение (оставьте пустым, чтобы не менять)',
            'status': 'Статус'
        }


class ListingFilterForm(forms.Form):
    """
    Форма фильтрации объявлений.
    """
    game = forms.ModelChoiceField(
        queryset=Game.objects.filter(is_active=True),
        required=False,
        empty_label='Все игры',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'От',
            'step': '0.01'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'До',
            'step': '0.01'
        })
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию...'
        })
    )
    
    SORT_CHOICES = [
        ('-created_at', 'Сначала новые'),
        ('created_at', 'Сначала старые'),
        ('price', 'Цена: по возрастанию'),
        ('-price', 'Цена: по убыванию'),
    ]
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

