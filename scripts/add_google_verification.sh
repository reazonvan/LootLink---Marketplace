#!/bin/bash

# Добавление Google Site Verification TXT записи в ISPmanager

echo "Добавляю Google Site Verification TXT-запись..."

# Используем API ISPmanager
# Или через curl запрос к панели

DOMAIN="lootlink.ru"
TXT_NAME="google-site-verification"
TXT_VALUE="sIZPJJwsVs72C3rERyKECmsPSzZ8jpBYZFVEbHMXjzI"

echo "Домен: $DOMAIN"
echo "Запись: $TXT_NAME=$TXT_VALUE"
echo ""

# Альтернативный способ - добавить через zone file
echo "✅ Запись будет добавлена вручную через ISPmanager"
echo "   Или используйте этот скрипт в панели управления"

