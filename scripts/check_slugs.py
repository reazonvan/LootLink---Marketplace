#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category

print("Игры:")
for g in Game.objects.all()[:5]:
    print(f"  {g.name} → slug: '{g.slug}'")

print("\nКатегории:")
for c in Category.objects.all()[:10]:
    print(f"  {c.game.name} / {c.name} → slug: '{c.slug}'")

