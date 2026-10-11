# finalproject_maslov_M26-555

# ValutaTrade Hub

Консольное приложение для учёта валютного и криптовалютного портфеля
с автоматическим обновлением курсов из внешних API.

Проект разделён на два сервиса:

- **Core** — бизнес-логика: пользователи, портфели, операции buy/sell, конвертация.
- **Parser Service** — получение курсов, кеширование, история обновлений, планировщик.

Core читает курсы из кеша `data/rates.json`, который наполняет Parser Service.
Это позволяет обновлять курсы независимо от работы CLI.

---

## Возможности

- Регистрация и вход пользователей (пароли хранятся хешированными).
- Портфель: покупка и продажа валют с проверкой остатка.
- Просмотр портфеля в любой базовой валюте.
- Курсы из двух независимых источников: CoinGecko (криптовалюты) и ExchangeRate-API (фиат).
- Кеширование курсов с TTL и автоматическим обновлением.
- Устойчивость к сбоям: недоступность одного источника не ломает обновление.
- Фоновый планировщик обновления курсов с корректным завершением по Ctrl+C.
- Аудит действий пользователя в лог-файл.

---

## Структура проекта

```
finalproject_maslov_M26-555/
├── main.py                          # точка входа CLI
├── pyproject.toml
├── .gitignore
├── README.md
├── data/                            # состояние приложения (не в git)
│   ├── rates.json                   # кеш курсов
│   ├── exchange_rates.json          # история обновлений
│   ├── users.json                   # пользователи
│   └── portfolios.json              # портфели
├── logs/                            # логи с ротацией (не в git)
│   └── actions.log
└── valutatrade_hub/
    ├── cli/
    │   └── interface.py             # разбор и обработка команд
    ├── core/
    │   ├── currencies.py            # справочник валют
    │   ├── exceptions.py            # исключения проекта
    │   ├── models.py                # User, Portfolio, Operation
    │   ├── usecases.py              # бизнес-логика
    │   └── utils.py                 # время, TTL, форматирование
    ├── infra/
    │   ├── database.py              # чтение/запись JSON
    │   ├── logging_config.py        # setup_logging(), get_logger()
    │   ├── logging_decorator.py     # @log_action — аудит действий
    │   └── settings.py              # настройки логирования
    └── parser_service/
        ├── api_clients.py           # CoinGeckoClient, ExchangeRateApiClient
        ├── config.py                # ParserConfig
        ├── scheduler.py             # фоновое обновление
        ├── storage.py               # чтение/запись курсов
        └── updater.py               # RatesUpdater.run_update()
```

---

## Установка

Проект использует [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/sirAlexMaslovsonVG/finalproject_maslov_M26-555
cd finalproject_maslov_M26-555
uv sync
```

---

## Быстрый старт

```bash
uv run python main.py
```

Пример сессии:

```text
ValutaTrade Hub. Введите help для списка команд.
> register --username erin --password 1234
> login --username erin --password 1234
Вы вошли как 'erin'
> update-rates
Обновлено пар: 4
- CoinGecko: 2 пар
- ExchangeRate-API: 2 пар
> buy --currency BTC --amount 0.001
> show-portfolio --base EUR
> exit
```

---

## Команды CLI

| Команда | Описание |
|:---|:---|
| `register --username <str> --password <str>` | регистрация пользователя |
| `login --username <str> --password <str>` | вход в систему |
| `logout` | выход |
| `show-portfolio [--base <str>]` | портфель в базовой валюте (по умолчанию USD) |
| `buy --currency <str> --amount <float>` | покупка валюты |
| `sell --currency <str> --amount <float>` | продажа валюты |
| `get-rate --from <str> --to <str>` | курс пары (прямой, обратный или кросс) |
| `show-rates` | текущие курсы из кеша |
| `update-rates` | принудительное обновление курсов |
| `help` | список команд |
| `exit` | выход |

---

## Parser Service

### Источники курсов

| Источник | Что даёт | Пример |
|:---|:---|:---|
| CoinGecko | криптовалюты | BTC→USD, ETH→USD |
| ExchangeRate-API | фиат | USD→RUB, USD→EUR |

### Обновление курсов

`RatesUpdater.run_update()`:

1. опрашивает каждый источник;
2. объединяет результаты (каждая пара хранит имя источника);
3. пишет историю в `data/exchange_rates.json`;
4. сохраняет кеш в `data/rates.json`;
5. возвращает `{"updated": int, "sources": {...}, "errors": {...}}`.

Если недоступны **все** источники — бросается `ApiRequestError`.
Если недоступен **один** — обновление продолжается, сбой попадает в `errors`.

### Планировщик

```bash
# один прогон и выход
uv run python -m valutatrade_hub.parser_service.scheduler --once

# бесконечный цикл (интервал из ParserConfig, по умолчанию 300 с)
uv run python -m valutatrade_hub.parser_service.scheduler

# бесконечный цикл с явным интервалом
uv run python -m valutatrade_hub.parser_service.scheduler --interval 600
```

Остановка — `Ctrl+C`: текущая итерация завершается, затем пишется лог и выход с кодом 0.

---

## Формат данных

### `data/rates.json`

```json
{
  "pairs": {
    "BTC_USD": {
      "rate": 83000.0,
      "source": "CoinGecko",
      "updated_at": "2026-10-11T12:46:30Z"
    },
    "USD_RUB": {
      "rate": 94.0,
      "source": "ExchangeRate-API",
      "updated_at": "2026-10-11T12:46:30Z"
    }
  },
  "last_refresh": "2026-10-11T12:46:30Z"
}
```

### `data/exchange_rates.json`

История снимков курсов с указанием источника и времени. Используется для аудита.

### Конвертация

Курс произвольной пары считается через USD:

- **прямой** — если в кеше есть `A_USD`;
- **обратный** — если есть `USD_A`, берётся `1 / rate`;
- **кросс** — `A→B = (A→USD) / (B→USD)`.

Пример: `EUR→RUB = (EUR→USD) / (RUB→USD)`.

---

## Логирование

Логи пишутся в `logs/actions.log` (JSON или text, настраивается в `infra/settings.py`)
с ротацией по размеру.

Пример записи:

```json
{"timestamp": "2026-10-11T15:46:30", "level": "INFO", "logger": "valutatrade",
 "message": "GET_RATE", "from_currency": "EUR", "to_currency": "RUB",
 "username": "erin", "result": "OK", "duration_ms": "415"}
```

Логи не дублируются в консоль намеренно: консоль отведена под вывод CLI,
аудит живёт в файле.

---

## Конфигурация

`valutatrade_hub/parser_service/config.py`:

| Параметр | Назначение | По умолчанию |
|:---|:---|:---|
| `RATES_FILE_PATH` | путь к кешу курсов | `data/rates.json` |
| `HISTORY_FILE_PATH` | путь к истории | `data/exchange_rates.json` |
| `REQUEST_TIMEOUT` | таймаут запроса к API, с | 10 |
| `SCHEDULER_INTERVAL` | интервал обновления, с | 300 |

Логирование — `valutatrade_hub/infra/settings.py`: `log_file`, `log_format` (`text`/`json`), `log_level`.

---

## Разработка

```bash
uv run ruff check .        # стиль (если настроен ruff)
```

### Полезно знать

- `data/*.json` и `logs/` исключены из git: это состояние запуска, а не код.
  После клона `data/` будет пустой — пользователи и портфели создаются заново.
- Если `update-rates` падает с `ApiRequestError` — проверьте доступность CoinGecko
  и ExchangeRate-API.
- Кеш считается свежим, пока не истёк TTL; при обращении Core к Parser Service
  курсы обновляются автоматически.