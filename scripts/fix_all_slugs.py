#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Исправление всех slug - транслитерация кириллицы
"""
import os, sys, django
from django.utils.text import slugify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category

# Транслитерация
TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}

def transliterate(text):
    result = []
    for char in text.lower():
        result.append(TRANSLIT.get(char, char))
    return ''.join(result)

def make_slug(text):
    translit = transliterate(text)
    return slugify(translit)[:120]

print("Исправление slug...")

fixed_games = 0
fixed_cats = 0

for game in Game.objects.all():
    new_slug = make_slug(game.name)
    if game.slug != new_slug:
        game.slug = new_slug
        game.save()
        fixed_games += 1
        print(f"✅ Game: {game.name} → {new_slug}")

for cat in Category.objects.all():
    new_slug = make_slug(cat.name)  # БЕЗ префикса игры!
    if cat.slug != new_slug:
        cat.slug = new_slug
        cat.save()
        fixed_cats += 1

print(f"\n✅ Исправлено игр: {fixed_games}")
print(f"✅ Исправлено категорий: {fixed_cats}")

