"""Точка входа ValutaTrade Hub."""

from valutatrade_hub.cli.interface import run_repl
from valutatrade_hub.infra.logging_config import setup_logging


def main() -> None:
    """Настраивает логирование и запускает REPL."""
    setup_logging()
    run_repl()


if __name__ == "__main__":
    main()
