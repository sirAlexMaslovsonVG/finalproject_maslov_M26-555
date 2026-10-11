"""Декоратор @log_action для аудита действий.

Логирует action, username, currency, amount, rate, base, result, error.
При исключении пишет error-поле и пробрасывает исключение дальше.
"""

import functools
import logging
import time

from valutatrade_hub.infra.logging_config import get_logger


def log_action(action: str, verbose: bool = False):
    """Декоратор, логирующий вызов функции как действие в аудите.

    Args:
        action: имя действия (например, «BUY», «SELL», «LOGIN»).
        verbose: если True — добавляет к записи входные аргументы.

    Returns:
        Декоратор для целевой функции.
    """

    def decorator(func):
        """Оборачивает функцию логированием до и после выполнения."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Выполняет функцию и пишет запись об успехе или ошибке."""
            logger = get_logger()
            started = time.perf_counter()

            fields = _extract_fields(kwargs, verbose)

            try:
                result = func(*args, **kwargs)
            except Exception as error:  # noqa: BLE001 - логируем и пробрасываем
                fields["result"] = "ERROR"
                fields["error"] = f"{type(error).__name__}: {error}"
                fields["duration_ms"] = _elapsed_ms(started)
                _log(logger, action, fields)
                raise

            fields["result"] = "OK"
            fields["duration_ms"] = _elapsed_ms(started)
            _log(logger, action, fields)
            return result

        return wrapper

    return decorator


def _extract_fields(kwargs: dict, verbose: bool) -> dict:
    """Извлекает «доменные» поля из аргументов вызова.

    Пытается достать username, currency, amount, rate, base.
    При verbose=True добавляет прочие аргументы как есть.
    """
    known = (
        "username",
        "currency",
        "amount",
        "rate",
        "base",
        "from_currency",
        "to_currency",
    )
    fields = {}

    for key in known:
        if key in kwargs:
            fields[key] = kwargs[key]

    if verbose:
        for key, value in kwargs.items():
            if key not in fields:
                fields[key] = value

    fields.setdefault("username", _current_username())
    return fields


def _current_username() -> str:
    """Возвращает имя текущего пользователя для контекста лога."""
    try:
        from valutatrade_hub.core import usecases

        user = usecases.get_current_user()
        return user.username if user else "anonymous"
    except Exception:  # noqa: BLE001 - логирование не должно ломать логику
        return "anonymous"


def _elapsed_ms(started: float) -> str:
    """Возвращает длительность операции в миллисекундах строкой."""
    return f"{(time.perf_counter() - started) * 1000:.0f}"


def _log(logger: logging.Logger, action: str, fields: dict) -> None:
    """Пишет запись в лог с доменными полями через extra."""
    logger.info(action, extra={"extra_fields": fields})
