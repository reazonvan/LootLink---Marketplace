# 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Редирект со страницы входа

## Проблема

Страница `/accounts/login/` **всегда редиректит на главную** (302 Found).

### Причина

Сервер считает что пользователь УЖЕ залогинен из-за:
1. Старых сессий в базе данных
2. Проблемы с куками сессии
3. Зависшей сессии reazonvan

### Диагностика

Network request показывает:
```
[GET] http://91.218.245.178/accounts/login/ => [302] Found (redirect to /)
```

Код в `accounts/views.py:34`:
```python
if request.user.is_authenticated:
    return redirect('listings:home')  # Вот это срабатывает!
```

---

## ✅ РЕШЕНИЕ

### 1. Очистить все сессии на сервере

```bash
ssh root@91.218.245.178

cd /opt/lootlink
source venv/bin/activate

# Очистить все сессии
python scripts/clear_sessions.py

# Перезапустить Gunicorn
sudo systemctl restart lootlink
```

### 2. Проверить логи

```bash
# Смотрим что происходит
sudo journalctl -u lootlink -n 100 --no-pager
```

### 3. Проверить в браузере

- Открыть режим инкогнито
- Очистить куки для 91.218.245.178
- Попробовать войти снова

---

## 🔍 Альтернативное решение

Если проблема сохраняется, временно **отключить проверку** для отладки:

```python
# accounts/views.py
def user_login(request):
    # Временно закомментировать для отладки:
    # if request.user.is_authenticated:
    #     return redirect('listings:home')
    
    if request.method == 'POST':
        ...
```

Но это **НЕ рекомендуется** для продакшена!

---

## 📋 Проверка

После исправления:
1. Открыть http://91.218.245.178/accounts/login/ - должна открыться страница входа
2. Ввести данные
3. Нажать "Войти" - должна произойти авторизация

---

Дата: 28.10.2025 23:00
Приоритет: КРИТИЧЕСКИЙ

