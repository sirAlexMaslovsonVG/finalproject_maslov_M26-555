"""Точка запуска приложения ValutaTrade Hub."""

from valutatrade_hub.cli import interface


def main() -> None:
    """Запускает консольный интерфейс."""
    interface.run_repl()


if __name__ == "__main__":
    main()
