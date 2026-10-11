"""Планировщик фонового обновления курсов.

Запуск:
    python -m valutatrade_hub.parser_service.scheduler            # цикл
    python -m valutatrade_hub.parser_service.scheduler --once     # один прогон
    python -m valutatrade_hub.parser_service.scheduler --interval 600

Планировщик не прерывает работу при ошибке обновления: сбой логируется,
и следующий цикл стартует через интервал.
"""

import argparse
import signal
import sys
import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.logging_config import get_logger, setup_logging
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = get_logger()

_stop_requested = False


def _handle_signal(signum, frame) -> None:
    """Обрабатывает Ctrl+C: просит цикл завершиться после текущего прогона."""
    global _stop_requested
    _stop_requested = True
    logger.info("Получен сигнал %s, завершаем после текущей итерации...", signum)


def run_once(config: ParserConfig | None = None) -> dict | None:
    """Выполняет одно обновление курсов.

    Args:
        config: настройки; если None — создаются по умолчанию.

    Returns:
        Результат run_update() либо None, если обновление не удалось.
    """
    config = config or ParserConfig()
    try:
        result = RatesUpdater(config).run_update()
    except ApiRequestError as error:
        logger.error("Обновление не удалось: %s", error)
        return None
    logger.info(
        "Обновлено пар: %s (%s)",
        result["updated"],
        ", ".join(result["sources"]) or "нет",
    )
    for source, error in result["errors"].items():
        logger.warning("Источник %s: %s", source, error)
    return result


def run_forever(
    config: ParserConfig | None = None, interval: int | None = None
) -> None:
    """Запускает бесконечный цикл обновления с заданным интервалом.

    Args:
        config: настройки; если None — создаются по умолчанию.
        interval: интервал в секундах; если None — берётся из конфига.
    """
    config = config or ParserConfig()
    interval = interval or config.SCHEDULER_INTERVAL
    logger.info("Планировщик запущен, интервал: %s с", interval)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not _stop_requested:
        started = time.monotonic()
        run_once(config)

        if _stop_requested:
            break

        # Спим интервал, но просыпаемся на сигнал не позже чем через секунду.
        while not _stop_requested and time.monotonic() - started < interval:
            time.sleep(min(1.0, interval - (time.monotonic() - started)))

    logger.info("Планировщик остановлен")


def _build_parser() -> argparse.ArgumentParser:
    """Собирает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Планировщик обновления курсов ValutaTrade Hub (Parser Service)."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="выполнить одно обновление и выйти",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="интервал между обновлениями в секундах (по умолчанию из конфига)",
    )
    return parser


def main(argv: list | None = None) -> int:
    """Точка входа планировщика.

    Args:
        argv: аргументы командной строки; если None — берутся из sys.argv.

    Returns:
        Код возврата процесса (0 — успех, 1 — ошибка).
    """
    setup_logging()
    args = _build_parser().parse_args(argv)
    config = ParserConfig()

    if args.once:
        result = run_once(config)
        return 0 if result is not None else 1

    run_forever(config, args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
