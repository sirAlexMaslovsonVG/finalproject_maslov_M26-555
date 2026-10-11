"""Вспомогательные функции ValutaTrade Hub."""

import json
from datetime import datetime, timedelta
from pathlib import Path

# --- Пути к файлам данных ---
# utils.py лежит в valutatrade_hub/core/, значит корень проекта — parents[2]

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"

# Формат ключа: "FROM_TO" — сколько единиц TO дают за 1 единицу FROM
STUB_EXCHANGE_RATES = {
    "USD_USD": 1.0,
    "EUR_USD": 1.0786,
    "RUB_USD": 0.01016,
    "BTC_USD": 59337.21,
    "ETH_USD": 3720.00,
}

# Время жизни курса в кеше (ТЗ: «моложе 5 минут»)
RATES_TTL_SECONDS = 300

# --- Работа с файлами ---


def ensure_data_files() -> None:
    """Создаёт папку data/ и пустые файлы, если их ещё нет."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")
    if not PORTFOLIOS_FILE.exists():
        PORTFOLIOS_FILE.write_text("[]", encoding="utf-8")
    if not RATES_FILE.exists():
        RATES_FILE.write_text("{}", encoding="utf-8")


def read_json(path: Path, default):
    """Читает JSON из файла; возвращает default, если файла нет или он пуст."""
    ensure_data_files()
    try:
        with path.open("r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                return default
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data) -> None:
    """Записывает данные в JSON-файл."""
    ensure_data_files()
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_users() -> list:
    """Возвращает список пользователей из users.json."""
    return read_json(USERS_FILE, default=[])


def save_users(users: list) -> None:
    """Сохраняет список пользователей в users.json."""
    write_json(USERS_FILE, users)


def load_portfolios() -> list:
    """Возвращает список портфелей из portfolios.json."""
    return read_json(PORTFOLIOS_FILE, default=[])


def save_portfolios(portfolios: list) -> None:
    """Сохраняет список портфелей в portfolios.json."""
    write_json(PORTFOLIOS_FILE, portfolios)


def load_rates() -> dict:
    """Возвращает кеш курсов из rates.json."""
    return read_json(RATES_FILE, default={})


def save_rates(rates: dict) -> None:
    """Сохраняет кеш курсов в rates.json."""
    write_json(RATES_FILE, rates)


# --- Время ---


def now_iso() -> str:
    """Текущее время в формате ISO (без микросекунд)."""
    return datetime.now().replace(microsecond=0).isoformat()


def is_fresh(updated_at: str, ttl_seconds: int = RATES_TTL_SECONDS) -> bool:
    """Проверяет, что метка времени моложе ttl_seconds (ТЗ: 5 минут)."""
    try:
        moment = datetime.fromisoformat(updated_at)
    except (TypeError, ValueError):
        return False
    return datetime.now() - moment < timedelta(seconds=ttl_seconds)


# --- Валидаторы (ТЗ, шаг 0) ---


def validate_amount(amount) -> float:
    """amount — положительное число (float > 0)."""
    try:
        value = float(amount)
    except (TypeError, ValueError) as error:
        raise ValueError("'amount' должен быть положительным числом") from error
    if value <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return value


def validate_currency_code(code) -> str:
    """currency_code — непустая строка, приводится к верхнему регистру."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return code.strip().upper()


# --- Сервис курсов (заглушка) ---


def refresh_rates() -> dict:
    """Обновляет кеш курсов заглушкой, если он устарел. Возвращает кеш."""
    rates = load_rates()
    last_refresh = rates.get("last_refresh")

    if last_refresh and is_fresh(last_refresh):
        return rates

    refreshed = {}
    for key, rate in STUB_EXCHANGE_RATES.items():
        refreshed[key] = {"rate": rate, "updated_at": now_iso()}
    refreshed["source"] = "StubRates (ParserService заглушка)"
    refreshed["last_refresh"] = now_iso()

    save_rates(refreshed)
    return refreshed
