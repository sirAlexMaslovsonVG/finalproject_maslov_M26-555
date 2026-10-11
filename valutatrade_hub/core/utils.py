"""Вспомогательные функции ValutaTrade Hub."""

from datetime import datetime, timedelta, timezone

from valutatrade_hub.infra.database import get_database
from valutatrade_hub.infra.settings import get_settings

# --- Работа с путями и JSON (через DatabaseManager) ---


def load_users() -> list:
    """Загружает список пользователей из users.json."""
    return get_database().load_users()


def save_users(users: list) -> None:
    """Сохраняет список пользователей в users.json."""
    get_database().save_users(users)


def load_portfolios() -> list:
    """Загружает список портфелей из portfolios.json."""
    return get_database().load_portfolios()


def save_portfolios(portfolios: list) -> None:
    """Сохраняет список портфелей в portfolios.json."""
    get_database().save_portfolios(portfolios)


def load_rates() -> dict:
    """Загружает кеш курсов из rates.json (весь файл: pairs + last_refresh)."""
    return get_database().load_rates()


def save_rates(rates: dict) -> None:
    """Сохраняет кеш курсов в rates.json."""
    get_database().save_rates(rates)


# --- Время ---


def now_iso() -> str:
    """Возвращает текущее время в ISO-8601 UTC с суффиксом 'Z'."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def is_fresh(updated_at: str, ttl_seconds: int | None = None) -> bool:
    """Проверяет, моложе ли метка времени указанного TTL.

    Корректно работает и с naive-метками (без таймзоны),
    и с aware-метками UTC (с суффиксом 'Z' или '+00:00').

    Args:
        updated_at: метка времени в формате ISO.
        ttl_seconds: время жизни в секундах; если None — берётся из настроек.

    Returns:
        True, если метка свежая; иначе False.
    """
    if not updated_at:
        return False
    if ttl_seconds is None:
        ttl_seconds = get_settings().get("rates_ttl_seconds", 300)
    try:
        moment = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False

    # Сравниваем в одном "сознании": aware-метку — с UTC-now,
    # naive-метку — с локальным now.
    now = datetime.now(moment.tzinfo) if moment.tzinfo else datetime.now()
    return now - moment < timedelta(seconds=ttl_seconds)


# --- Курсы (интеграция с Parser Service, разделы 4–5 ТЗ) ---


def refresh_rates() -> dict:
    """Возвращает актуальные курсы: из кеша, если свежий, иначе через Parser Service.

    Returns:
        Словарь пар вида {'BTC_USD': {'rate': ..., 'updated_at': ...}}.

    Raises:
        ApiRequestError: если обновление не удалось и кеш отсутствует/устарел.
    """
    from valutatrade_hub.core.exceptions import ApiRequestError

    cache = load_rates()
    if not isinstance(cache, dict):
        cache = {}

    last_refresh = cache.get("last_refresh")
    if last_refresh and is_fresh(last_refresh) and cache.get("pairs"):
        return cache["pairs"]

    # Ленивый импорт: разрываем цикл utils -> updater -> storage -> utils.
    from valutatrade_hub.parser_service.config import ParserConfig
    from valutatrade_hub.parser_service.updater import RatesUpdater

    updater = RatesUpdater(ParserConfig())
    updater.run_update()  # бросит ApiRequestError при полном сбое

    refreshed = load_rates()
    if not isinstance(refreshed, dict):
        raise ApiRequestError("кеш курсов повреждён после обновления")
    return refreshed.get("pairs", {})


# --- Валидаторы (раздел 2.2 ТЗ) ---


def validate_amount(amount) -> float:
    """Проверяет, что сумма — положительное число.

    Args:
        amount: значение для проверки (может быть строкой).

    Returns:
        Сумма как float.

    Raises:
        ValueError: если сумма не число или не больше нуля.
    """
    try:
        value = float(amount)
    except (TypeError, ValueError) as error:
        raise ValueError("'amount' должен быть положительным числом") from error
    if value <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return value


def validate_currency_code(code: str) -> str:
    """Проверяет, что код валюты — непустая строка; приводит к верхнему регистру."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return code.strip().upper()


# --- Форматирование вывода (формат ТЗ) ---


def format_amount(amount: float, currency_code: str) -> str:
    """Форматирует сумму по правилам ТЗ.

    Фиатные валюты — 2 знака после запятой, криптовалюты — 4.
    """
    from valutatrade_hub.core.currencies import is_fiat

    digits = 2 if is_fiat(currency_code) else 4
    return f"{amount:.{digits}f}"
