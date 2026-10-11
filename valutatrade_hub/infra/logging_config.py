"""Настройка логирования ValutaTrade Hub.

Единая точка инициализации логгера: RotatingFileHandler с ротацией
по размеру, формат записи text или json, уровень из конфигурации.
"""

import json
import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import get_settings

_LOGGER_NAME = "valutatrade"
_configured = False

# Ротация по размеру: 1 MB на файл, 3 архивных копии (actions.log.1 … .3).
_MAX_BYTES = 1_048_576
_BACKUP_COUNT = 3


class JsonFormatter(logging.Formatter):
    """Форматтер, собирающий запись лога в одну JSON-строку.

    Доменные поля (action, username, currency, amount, rate …)
    попадают в JSON через record.extra_fields, который добавляет
    декоратор @log_action.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Сериализует запись лога в JSON."""
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Форматтер для человекочитаемого текстового лога.

    Формат: ISO-timestamp | LEVEL | message | key=value ...
    """

    def format(self, record: logging.LogRecord) -> str:
        """Собирает текстовую строку лога с полями через 'ключ=значение'."""
        timestamp = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        parts = [timestamp, record.levelname, record.getMessage()]

        extra = getattr(record, "extra_fields", {})
        for key, value in extra.items():
            parts.append(f"{key}={value}")

        line = " | ".join(parts)
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def _build_formatter(log_format: str) -> logging.Formatter:
    """Возвращает форматтер по имени формата из конфигурации."""
    if log_format == "json":
        return JsonFormatter()
    return TextFormatter()


def setup_logging() -> logging.Logger:
    """Настраивает и возвращает корневой логгер проекта.

    Инициализация выполняется один раз на процесс (идемпотентно),
    чтобы повторные вызовы не плодили дублирующие обработчики.

    Returns:
        Настроенный логгер 'valutatrade'.
    """
    global _configured

    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger

    settings = get_settings()

    log_file = settings.get("log_file", "logs/actions.log")
    log_format = settings.get("log_format", "text")
    log_level = settings.get("log_level", "INFO")

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger.setLevel(getattr(logging, str(log_level).upper(), logging.INFO))
    logger.propagate = False

    handler = RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(_build_formatter(log_format))
    logger.addHandler(handler)

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    """Возвращает настроенный логгер проекта (с ленивой инициализацией)."""
    return setup_logging()
