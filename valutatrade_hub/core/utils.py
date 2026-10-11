"""Вспомогательные функции ValutaTrade Hub."""

from datetime import datetime, timedelta

from valutatrade_hub.infra.database import get_database
from valutatrade_hub.infra.settings import get_settings

# Заглушка курсов до подключения Parser Service (раздел 5 ТЗ).
STUB_RATES = {
    "EUR_USD": 1.0786,
    "BTC_USD": 59337.21,
    "RUB_USD": 0.01016,
    "ETH_USD": 3720.00,
}
STUB_RATES_SOURCE = "StubRates (ParserService заглушка)"

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
    """Загружает кеш курсов из rates.json."""
    return get_database().load_rates()


def save_rates(rates: dict) -> None:
    """Сохраняет кеш курсов в rates.json."""
    get_database().save_rates(rates)


# --- Время ---


def now_iso() -> str:
    """Возвращает текущее время в формате ISO без микросекунд."""
    return datetime.now().replace(microsecond=0).isoformat()


def is_fresh(updated_at: str, ttl_seconds: int | None = None) -> bool:
    """Проверяет, моложе ли метка времени указанного TTL.

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
        moment = datetime.fromisoformat(updated_at)
    except ValueError:
        return False
    return datetime.now() - moment < timedelta(seconds=ttl_seconds)


# --- Курсы (заглушка Parser Service) ---


def refresh_rates() -> dict:
    """Возвращает актуальные курсы: из кеша, если свежий, иначе обновляет.

    Пока Parser Service не подключён, источник — заглушка STUB_RATES.

    Returns:
        Словарь курсов в формате rates.json.
    """
    rates = load_rates()
    last_refresh = rates.get("last_refresh")
    if last_refresh and is_fresh(last_refresh):
        return rates

    updated_at = now_iso()
    refreshed = {
        pair: {"rate": rate, "updated_at": updated_at}
        for pair, rate in STUB_RATES.items()
    }
    refreshed["source"] = STUB_RATES_SOURCE
    refreshed["last_refresh"] = updated_at
    save_rates(refreshed)
    return refreshed


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
