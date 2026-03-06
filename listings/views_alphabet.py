"""
Алфавитный каталог игр (как у FunPay).
"""
from django.shortcuts import render
from django.db.models import Count, Q
from .models import Game


def games_catalog_alphabetical(request):
    """
    Каталог игр с алфавитной навигацией.
    Группирует игры по первой букве названия.
    """
    # Получаем все активные игры с подсчетом объявлений
    games = Game.objects.filter(is_active=True).annotate(
        listings_count=Count('listings', filter=Q(listings__status='active'))
    ).order_by('name')

    # Группировка по первой букве
    alphabet = {}
    alphabet_order = []

    for game in games:
        # Определяем первую букву
        first_char = game.name[0].upper()

        # Для латиницы, кириллицы и цифр
        if first_char.isalpha():
            letter = first_char
        elif first_char.isdigit():
            letter = '#'
        else:
            letter = '#'

        # Добавляем в словарь
        if letter not in alphabet:
            alphabet[letter] = []
            alphabet_order.append(letter)

        alphabet[letter].append(game)

    # Сортируем буквы: сначала кириллица, потом латиница, потом #
    def sort_key(letter):
        if letter == '#':
            return (2, letter)
        elif 'А' <= letter <= 'Я':
            return (0, letter)
        else:
            return (1, letter)

    alphabet_order.sort(key=sort_key)

    # Создаем упорядоченный список для шаблона
    alphabet_sorted = [(letter, alphabet[letter]) for letter in alphabet_order]

    context = {
        'alphabet': alphabet_sorted,
        'alphabet_letters': alphabet_order,
        'total_games': games.count(),
    }

    return render(request, 'listings/games_alphabet.html', context)
