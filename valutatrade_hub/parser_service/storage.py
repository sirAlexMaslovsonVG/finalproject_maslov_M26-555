"""Хранилище Parser Service.

Отвечает за два файла:
- exchange_rates.json — история замеров (журнал);
- rates.json — кеш последних значений для Core Service.

Запись во все файлы атомарная: временный файл → os.replace.
"""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("valutatrade")


def _utc_now_iso() -> str:
    """Возвращает текущее время в ISO-8601 UTC с суффиксом 'Z'.

    Returns:
        Строка вида '2025-10-10T12:00:00Z'.
    """
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _atomic_write(path: str, payload: object) -> None:
    """Атомарно записывает JSON в файл (tmp → rename).

    Args:
        path: путь к результирующему файлу.
        payload: сериализуемые данные.
    """
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _read_json(path: str, default):
    """Читает JSON-файл, возвращая default при отсутствии/поломке.

    Args:
        path: путь к файлу.
        default: значение при отсутствии или некорректном JSON.

    Returns:
        Разобранный JSON или default.
    """
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError) as error:
        logger.warning("Не удалось прочитать %s: %s", path, error)
        return default


def _split_pair(pair: str) -> tuple:
    """Разбивает 'BTC_USD' на ('BTC', 'USD').

    Args:
        pair: строка пары вида '<FROM>_<TO>'.

    Returns:
        Кортеж из двух кодов в верхнем регистре.
    """
    parts = pair.split("_", 1)
    return parts[0].upper(), parts[1].upper()


def append_history(history_path: str, rates: dict, source: str) -> int:
    """Дописывает замеры в историю exchange_rates.json.

    Args:
        history_path: путь к файлу истории.
        rates: словарь {'BTC_USD': 82970.0, ...}.
        source: имя источника (например, 'CoinGecko').

    Returns:
        Количество добавленных записей.
    """
    history = _read_json(history_path, [])
    timestamp = _utc_now_iso()

    added = 0
    for pair, rate in rates.items():
        from_currency, to_currency = _split_pair(pair)
        record_id = f"{from_currency}_{to_currency}_{timestamp}"
        history.append(
            {
                "id": record_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": float(rate),
                "timestamp": timestamp,
                "source": source,
                "meta": {},
            }
        )
        added += 1

    _atomic_write(history_path, history)
    return added


def save_rates(rates_path: str, rates: dict, sources: dict) -> None:
    """Сохраняет срез курсов в rates.json (в формате 'pairs').

    Обновляет пару только если новый updated_at свежее текущего.

    Args:
        rates_path: путь к кешу Core Service.
        rates: словарь {'BTC_USD': 83117.0, ...}.
        sources: словарь {'BTC_USD': 'CoinGecko', ...} — источник каждой пары.
    """
    cache = _read_json(rates_path, {})
    pairs = cache.get("pairs", {})
    timestamp = _utc_now_iso()

    for pair, rate in rates.items():
        existing = pairs.get(pair)
        if existing and existing.get("updated_at", "") >= timestamp:
            continue
        pairs[pair] = {
            "rate": float(rate),
            "updated_at": timestamp,
            "source": sources.get(pair, "unknown"),
        }

    payload = {
        "pairs": pairs,
        "last_refresh": timestamp,
    }
    _atomic_write(rates_path, payload)


def load_rates(rates_path: str) -> dict:
    """Читает кеш rates.json.

    Args:
        rates_path: путь к файлу кеша.

    Returns:
        Словарь кеша или пустой словарь, если файла нет.
    """
    return _read_json(rates_path, {})
