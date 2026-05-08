# Locust — нагрузочное тестирование LootLink

## Установка

```bash
pip install locust
```

## Запуск (Web UI)

```bash
locust -f tests/locust/locustfile.py --host=http://localhost:8000
```

Открыть `http://localhost:8089`, установить:
- **Number of users:** 100
- **Spawn rate:** 10 users/sec
- **Run time:** 5m

Нажать **Start swarming**.

## Headless (для CI / отчёта)

```bash
locust -f tests/locust/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --csv=results/locust \
    --html=results/locust_report.html
```

## Сценарии

### `AnonBrowsingUser` (основной трафик, ~80%)
- Главная страница (вес 5)
- Каталог игр (вес 3)
- Список объявлений с пагинацией (вес 2)
- FTS-поиск (вес 2)
- Детальная карточка (вес 1)

### `AuthenticatedUser` (~10%)
- Профиль, мои объявления
- Кошелёк, транзакции
- Список диалогов
- Сделки

Требует pre-existing user (логин при `on_start`):
```bash
export LOCUST_USER=demo_buyer
export LOCUST_PASSWORD=demo_pass
```

### `APIUser` (~10%)
- `/api/listings/`
- `/api/games/`
- `/api/listings/[id]/`

## Ожидаемые метрики (на одной машине, 1 vCPU, 1 GB RAM)

| Метрика | Цель | Прод |
|---|---|---|
| RPS | ≥ 200 | ~600 (4 vCPU) |
| p50 latency | ≤ 100 мс | 80 мс |
| p95 latency | ≤ 250 мс | 187 мс |
| p99 latency | ≤ 500 мс | 350 мс |
| Failures | ≤ 0.1% | 0% |

## Для дипломного отчёта (раздел 2.4)

Скриншоты Web UI с метриками:
1. График RPS / Response time
2. Таблица endpoints с p95/p99
3. Distribution chart (запросов по типам)
4. Total RPS / failures на пиковой нагрузке

CSV-отчёт `results/locust_stats.csv` — для таблиц в .docx.
