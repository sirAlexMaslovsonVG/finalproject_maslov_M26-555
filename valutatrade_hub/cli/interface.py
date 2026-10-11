"""Командный интерфейс ValutaTrade Hub."""

import shlex

from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import list_currencies
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.utils import format_amount

HELP_TEXT = """Доступные команды:
  register --username <str> --password <str>
  login --username <str> --password <str>
  logout
  show-portfolio [--base <str>]
  buy --currency <str> --amount <float>
  sell --currency <str> --amount <float>
  get-rate --from <str> --to <str>
  show-rates
  update-rates
  help
  exit
"""


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


def _require_arg(args: dict, name: str) -> str:
    """Возвращает значение обязательного аргумента или бросает ошибку."""
    if name not in args:
        raise ValueError(f"Не указан обязательный аргумент '--{name}'")
    return args[name]


# --- Обработчики команд ---


def _handle_register(args: dict) -> None:
    """Команда register --username <str> --password <str>."""
    message = usecases.register(
        username=_require_arg(args, "username"),
        password=_require_arg(args, "password"),
    )
    print(message)


def _handle_login(args: dict) -> None:
    """Команда login --username <str> --password <str>."""
    message = usecases.login(
        username=_require_arg(args, "username"),
        password=_require_arg(args, "password"),
    )
    print(message)


def _handle_logout(args: dict) -> None:
    """Команда logout."""
    if usecases.get_current_user() is None:
        print("Вы не авторизованы")
        return
    usecases.logout()
    print("Вы вышли из системы")


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
        code = item["currency"]
        balance = format_amount(item["balance"], code)
        value = format_amount(item["value"], result["base"])
        print(f"- {code}: {balance}  → {value} {result['base']}")

    print("-" * 33)
    total = format_amount(result["total"], result["base"])
    print(f"ИТОГО: {total} {result['base']}")


def _handle_buy(args: dict) -> None:
    """Команда buy --currency <str> --amount <float>."""
    currency = _require_arg(args, "currency").upper()
    amount = _require_arg(args, "amount")

    # 3.5: недоступный курс -> отдельное сообщение из ТЗ (раздел 2.2).
    try:
        result = usecases.buy(currency=currency, amount=amount)
    except ApiRequestError:
        print(f"Не удалось получить курс для {currency}→USD")
        return

    code = result["currency"]
    rate = f"{result['rate']:,.2f}"
    print(
        f"Покупка выполнена: {result['amount']:.4f} {code} по курсу {rate} USD/{code}"
    )
    print("Изменения в портфеле:")
    print(f"- {code}: было {result['before']:.4f} → стало {result['after']:.4f}")
    print(f"Оценочная стоимость покупки: {result['cost']:,.2f} USD")


def _handle_sell(args: dict) -> None:
    """Команда sell --currency <str> --amount <float>."""
    currency = _require_arg(args, "currency").upper()
    amount = _require_arg(args, "amount")

    # 3.5: недоступный курс -> отдельное сообщение из ТЗ (раздел 2.2).
    try:
        result = usecases.sell(currency=currency, amount=amount)
    except ApiRequestError:
        print(f"Не удалось получить курс для {currency}→USD")
        return

    code = result["currency"]
    rate = f"{result['rate']:,.2f}"
    print(
        f"Продажа выполнена: {result['amount']:.4f} {code} по курсу {rate} USD/{code}"
    )
    print("Изменения в портфеле:")
    print(f"- {code}: было {result['before']:.4f} → стало {result['after']:.4f}")
    print(f"Оценочная выручка: {result['revenue']:,.2f} USD")


def _format_rate(value: float) -> str:
    """Форматирует значение курса для вывода.

    Очень маленькие значения выводятся с 8 знаками, крупные — с 2,
    чтобы совпасть с примерами и не терять точность для крипты.

    Args:
        value: значение курса.

    Returns:
        Отформатированная строка.
    """
    if value and abs(value) < 1:
        return f"{value:.8f}"
    return f"{value:,.2f}"


def _handle_get_rate(args: dict) -> None:
    """Команда get-rate --from <str> --to <str>."""
    from_code = _require_arg(args, "from").upper()
    to_code = _require_arg(args, "to").upper()

    # 3.5: недоступный источник -> сообщение из ТЗ (раздел 2.2).
    try:
        result = usecases.get_rate(from_currency=from_code, to_currency=to_code)
    except ApiRequestError:
        print(f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже.")
        return

    updated = result["updated_at"].replace("T", " ")
    print(
        f"Курс {result['from']}→{result['to']}: {_format_rate(result['rate'])} "
        f"(обновлено: {updated})"
    )
    if result["rate"]:
        print(
            f"Обратный курс {result['to']}→{result['from']}: "
            f"{_format_rate(1 / result['rate'])}"
        )


def _handle_update_rates(args: dict) -> None:
    """Команда update-rates — принудительное обновление курсов через Parser Service."""
    from valutatrade_hub.parser_service.config import ParserConfig
    from valutatrade_hub.parser_service.updater import RatesUpdater

    result = RatesUpdater(ParserConfig()).run_update()
    print(f"Обновлено пар: {result['updated']}")
    for source, count in result["sources"].items():
        print(f"- {source}: {count} пар")
    for source, error in result["errors"].items():
        print(f"- {source}: ошибка — {error}")


def _handle_show_rates(args: dict) -> None:
    """Команда show-rates — вывод последних сохранённых курсов."""
    result = usecases.show_rates()
    pairs = result["pairs"]
    if not pairs:
        print("Курсы отсутствуют. Выполните: update-rates")
        return

    print("Последние сохранённые курсы:")
    for pair, entry in sorted(pairs.items()):
        rate = _format_rate(entry["rate"])
        updated = str(entry.get("updated_at", "")).replace("T", " ")
        source = entry.get("source", "неизвестно")
        print(f"- {pair}: {rate} (обновлено: {updated}, источник: {source})")
    if result["last_refresh"]:
        print(f"Последнее обновление: {str(result['last_refresh']).replace('T', ' ')}")


COMMANDS = {
    "register": _handle_register,
    "login": _handle_login,
    "logout": _handle_logout,
    "show-portfolio": _handle_show_portfolio,
    "buy": _handle_buy,
    "sell": _handle_sell,
    "get-rate": _handle_get_rate,
    "show-rates": _handle_show_rates,
    "update-rates": _handle_update_rates,
}


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
    except InsufficientFundsError as error:
        print(error)
    except CurrencyNotFoundError as error:
        print(error)
        supported = ", ".join(list_currencies())
        print(f"Поддерживаемые коды: {supported}. Справка: help get-rate")
    except ApiRequestError as error:
        print(error)
        print("Повторите попытку позже или проверьте соединение.")
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
