"""
Скрипт для создания базы данных PostgreSQL
"""
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Подключаемся к PostgreSQL
try:
    connection = psycopg2.connect(
        user="postgres",
        password="5906639Pe",
        host="localhost",
        port="5432",
        database="postgres"  # подключаемся к дефолтной БД
    )
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    
    # Проверяем, существует ли база данных
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'lootlink_db'")
    exists = cursor.fetchone()
    
    if exists:
        print("[!] База данных lootlink_db уже существует")
    else:
        # Создаем базу данных
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier('lootlink_db')
        ))
        print("[+] База данных lootlink_db успешно создана!")
    
    cursor.close()
    connection.close()
    print("\n[OK] Готово! Теперь можно применять миграции.")
    
except psycopg2.Error as e:
    print(f"[ERROR] Ошибка подключения к PostgreSQL: {e}")
    print("\nПроверьте:")
    print("1. PostgreSQL запущен?")
    print("2. Пароль правильный?")
    print("3. Порт 5432 доступен?")
except Exception as e:
    print(f"[ERROR] Ошибка: {e}")

