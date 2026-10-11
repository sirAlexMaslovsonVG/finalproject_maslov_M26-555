"""Командный интерфейс ValutaTrade Hub."""

import shlex

from valutatrade_hub.core import usecases

# Справка по доступным командам (раздел 2.2 ТЗ)
HELP_TEXT = """Доступные команды:
  register --username <str> --password <str>
  login --username <str> --password <str>
  show-portfolio [--base <str>]
  buy --currency <str> --amount <float>
  sell --currency <str> --amount <float>
  get-rate --from <str> --to <str>
  help
  logout
  exit
"""

# --- Разбор аргументов вида --key value ---


def _parse_args(tokens: list) -> dict:
    """Превращает ['--username', 'alice'] в {'username': 'alice'}."""
    args = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            raise ValueError(f"Неверный аргумент '{token}'")
        key = token[2:]
        if index + 1 >= len(tokens):
            raise ValueError(f"Не указано значение для '{token}'")
        args[key] = tokens[index + 1]
        index += 2
    return args


# --- Обработчики команд ---


def _handle_register(args: dict) -> None:
    """Команда register --username <str> --password <str>."""
    if "username" not in args:
        raise ValueError("Не указан обязательный аргумент '--username'")
    if "password" not in args:
        raise ValueError("Не указан обязательный аргумент '--password'")
    message = usecases.register(args["username"], args["password"])
    print(message)


def _handle_login(args: dict) -> None:
    """Команда login --username <str> --password <str>."""
    if "username" not in args:
        raise ValueError("Не указан обязательный аргумент '--username'")
    if "password" not in args:
        raise ValueError("Не указан обязательный аргумент '--password'")
    message = usecases.login(args["username"], args["password"])
    print(message)


# --- Основной разбор и запуск ---


def execute_line(line: str) -> str | None:
    """Разбирает строку команды и выполняет её.

    Returns:
        'exit' — если пользователь хочет выйти; иначе None.
    """
    line = line.strip()
    if not line:
        return None

    try:
        tokens = shlex.split(line)
    except ValueError as error:
        print(f"Ошибка ввода: {error}")
        return None

    command, *rest = tokens

    if command in ("exit", "quit"):
        return "exit"

    if command in ("help", "?"):
        print(HELP_TEXT)
        return None

    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Неизвестная команда '{command}'. Введите help для справки.")
        return None

    try:
        args = _parse_args(rest)
        handler(args)
    except (ValueError, KeyError, PermissionError) as error:
        print(error)

    return None


def run_repl() -> None:
    """Запускает цикл чтения команд (REPL)."""
    print("ValutaTrade Hub. Введите help для списка команд.")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if execute_line(line) == "exit":
            break


def _handle_show_portfolio(args: dict) -> None:
    """Команда show-portfolio [--base <str>]."""
    base = args.get("base", "USD")
    result = usecases.show_portfolio(base)

    print(f"Портфель пользователя '{result['user']}' (база: {result['base']}):")
    if not result["wallets"]:
        print("  Кошельки отсутствуют.")
        print(f"ИТОГО: 0.00 {result['base']}")
        return

    for item in result["wallets"]:
        print(
            f"- {item['currency']}: {item['balance']:.4f} "
            f"→ {item['value']:,.2f} {result['base']}"
        )
    print("-" * 33)
    print(f"ИТОГО: {result['total']:,.2f} {result['base']}")


def _handle_logout(args: dict) -> None:
    """Команда logout."""
    usecases.logout()
    print("Вы вышли из системы")


# Таблица команд: имя -> обработчик
COMMANDS = {
    "register": _handle_register,
    "login": _handle_login,
    "show-portfolio": _handle_show_portfolio,
    "logout": _handle_logout,
}
