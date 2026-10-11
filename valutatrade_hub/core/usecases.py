"""Бизнес-логика ValutaTrade Hub."""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core import utils
from valutatrade_hub.core.models import Portfolio, User, Wallet

# --- Текущая сессия (в памяти процесса) ---
_current_user: User | None = None


def get_current_user() -> User | None:
    """Возвращает текущего залогиненного пользователя или None."""
    return _current_user


# --- Сборка объекта User из записи в users.json ---


def _user_from_record(record: dict) -> User:
    """Преобразует словарь из users.json в объект User."""
    return User(
        user_id=record["user_id"],
        username=record["username"],
        hashed_password=record["hashed_password"],
        salt=record["salt"],
        registration_date=datetime.fromisoformat(record["registration_date"]),
    )


def _record_from_user(user: User) -> dict:
    """Преобразует объект User в словарь для users.json."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(),
    }


def _next_user_id(users: list) -> int:
    """Автоинкремент user_id."""
    if not users:
        return 1
    return max(record["user_id"] for record in users) + 1


# --- Команда register ---


def register(username: str, password: str) -> str:
    """Создаёт нового пользователя и пустой портфель.

    Args:
        username: имя пользователя (не пустое, уникальное).
        password: пароль (не короче 4 символов).

    Returns:
        Сообщение об успешной регистрации.
    """
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    username = username.strip()

    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = utils.load_users()
    for record in users:
        if record["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = _next_user_id(users)

    salt = secrets.token_hex(4)
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    registration_date = datetime.now().replace(microsecond=0)

    user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed,
        salt=salt,
        registration_date=registration_date,
    )

    users.append(_record_from_user(user))
    utils.save_users(users)

    portfolios = utils.load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    utils.save_portfolios(portfolios)

    return (
        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


# --- Команда login ---


def login(username: str, password: str) -> str:
    """Входит в систему и фиксирует текущую сессию.

    Args:
        username: имя пользователя.
        password: пароль.

    Returns:
        Сообщение об успешном входе.
    """
    global _current_user

    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    users = utils.load_users()
    record = None
    for item in users:
        if item["username"] == username:
            record = item
            break

    if record is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = _user_from_record(record)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    _current_user = user
    return f"Вы вошли как '{username}'"


def logout() -> None:
    """Завершает сессию текущего пользователя."""
    global _current_user
    _current_user = None


def _require_login() -> User:
    """Возвращает залогиненного пользователя или бросает ошибку."""
    if _current_user is None:
        raise PermissionError("Сначала выполните login")
    return _current_user


# --- Сборка/запись портфеля ---


def _portfolio_from_record(record: dict, user: User) -> Portfolio:
    """Преобразует запись из portfolios.json в объект Portfolio."""
    wallets = {}
    for code, data in record.get("wallets", {}).items():
        wallets[code] = Wallet(currency_code=code, balance=data.get("balance", 0.0))
    return Portfolio(user_id=record["user_id"], user=user, wallets=wallets)


def _record_from_portfolio(portfolio: Portfolio) -> dict:
    """Преобразует объект Portfolio в словарь для portfolios.json."""
    return {
        "user_id": portfolio.user_id,
        "wallets": {
            code: {"balance": wallet.balance}
            for code, wallet in portfolio.wallets.items()
        },
    }


def _find_portfolio_record(portfolios: list, user_id: int) -> dict:
    """Находит запись портфеля по user_id."""
    for record in portfolios:
        if record["user_id"] == user_id:
            return record
    raise KeyError(f"Портфель пользователя id={user_id} не найден")


# --- Команда show-portfolio ---


def show_portfolio(base_currency: str = "USD") -> dict:
    """Считает портфель пользователя в базовой валюте.

    Args:
        base_currency: базовая валюта конвертации (по умолчанию USD).

    Returns:
        Словарь с именем пользователя, базой, строками кошельков и итогом.
    """
    user = _require_login()
    base = utils.validate_currency_code(base_currency)

    rates = utils.refresh_rates()

    if base != "USD" and f"{base}_USD" not in rates:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")

    portfolios = utils.load_portfolios()
    record = _find_portfolio_record(portfolios, user.user_id)
    portfolio = _portfolio_from_record(record, user)

    wallets_info = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        rate = _rate_to_base(code, base, rates)
        value = wallet.balance * rate
        total += value
        wallets_info.append(
            {"currency": code, "balance": wallet.balance, "value": value}
        )

    return {
        "user": user.username,
        "base": base,
        "wallets": wallets_info,
        "total": total,
    }


def _rate_to_base(currency: str, base: str, rates: dict) -> float:
    """Возвращает курс currency → base по кешу rates.json."""
    if currency == base:
        return 1.0

    direct = f"{currency}_{base}"
    if direct in rates:
        return rates[direct]["rate"]

    reverse = f"{base}_{currency}"
    if reverse in rates:
        return 1.0 / rates[reverse]["rate"]

    # через USD как промежуточную валюту
    to_usd = f"{currency}_USD"
    base_usd = f"{base}_USD"
    if to_usd in rates and base_usd in rates:
        return rates[to_usd]["rate"] / rates[base_usd]["rate"]

    raise ValueError(f"Курс для {currency}→{base} недоступен")


# --- Команды buy / sell ---


def _load_portfolio() -> tuple[Portfolio, list]:
    """Загружает портфель текущего пользователя вместе со списком записей."""
    user = _require_login()
    portfolios = utils.load_portfolios()
    record = _find_portfolio_record(portfolios, user.user_id)
    return _portfolio_from_record(record, user), portfolios


def buy(currency: str, amount) -> dict:
    """Покупает валюту: увеличивает баланс кошелька на amount.

    Args:
        currency: код покупаемой валюты.
        amount: количество в штуках (не в долларах), > 0.

    Returns:
        Данные об операции для вывода в CLI.
    """
    code = utils.validate_currency_code(currency)
    value = utils.validate_amount(amount)

    portfolio, portfolios = _load_portfolio()

    if code not in portfolio.wallets:
        portfolio.add_currency(code)

    wallet = portfolio.get_wallet(code)
    before = wallet.balance
    wallet.deposit(value)
    after = wallet.balance

    _save_portfolio(portfolio, portfolios)

    rates = utils.refresh_rates()
    try:
        rate = _rate_to_base(code, "USD", rates)
    except ValueError as error:
        raise ValueError(f"Не удалось получить курс для {code}→USD") from error

    return {
        "currency": code,
        "amount": value,
        "before": before,
        "after": after,
        "rate": rate,
        "cost": value * rate,
    }


def sell(currency: str, amount) -> dict:
    """Продаёт валюту: уменьшает баланс кошелька на amount.

    Args:
        currency: код продаваемой валюты.
        amount: количество в штуках, > 0.

    Returns:
        Данные об операции для вывода в CLI.
    """
    code = utils.validate_currency_code(currency)
    value = utils.validate_amount(amount)

    portfolio, portfolios = _load_portfolio()

    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )

    wallet = portfolio.get_wallet(code)
    before = wallet.balance

    if value > before:
        raise ValueError(
            f"Недостаточно средств: доступно {before:.4f} {code}, "
            f"требуется {value:.4f} {code}"
        )

    wallet.withdraw(value)
    after = wallet.balance

    _save_portfolio(portfolio, portfolios)

    rates = utils.refresh_rates()
    try:
        rate = _rate_to_base(code, "USD", rates)
    except ValueError as error:
        raise ValueError(f"Не удалось получить курс для {code}→USD") from error

    return {
        "currency": code,
        "amount": value,
        "before": before,
        "after": after,
        "rate": rate,
        "revenue": value * rate,
    }


# --- Команда get-rate ---


def get_rate(from_currency: str, to_currency: str) -> dict:
    """Возвращает курс обмена из валюты в валюту.

    Логика:
      1. Если пара есть в кеше и он свежий — берём из кеша.
      2. Иначе обновляем кеш (заглушка «парсера») и берём оттуда.

    Args:
        from_currency: исходная валюта.
        to_currency: целевая валюта.

    Returns:
        Словарь с парой, значением, временем обновления и источником.
    """
    _require_login()

    source = utils.validate_currency_code(from_currency)
    target = utils.validate_currency_code(to_currency)

    rates = utils.load_rates()
    last_refresh = rates.get("last_refresh")

    if not last_refresh or not utils.is_fresh(last_refresh):
        rates = utils.refresh_rates()

    key = f"{source}_{target}"

    if key in rates:
        entry = rates[key]
        return {
            "pair": key,
            "rate": entry["rate"],
            "updated_at": entry["updated_at"],
            "source": rates.get("source", "неизвестно"),
        }

    try:
        rate = _rate_to_base(source, target, rates)
    except ValueError as error:
        raise ValueError(f"Не удалось получить курс '{source}→{target}'") from error

    return {
        "pair": key,
        "rate": rate,
        "updated_at": last_refresh or utils.now_iso(),
        "source": rates.get("source", "неизвестно"),
    }


def _save_portfolio(portfolio: Portfolio, portfolios: list) -> None:
    """Записывает изменённый портфель обратно в portfolios.json."""
    for index, record in enumerate(portfolios):
        if record["user_id"] == portfolio.user_id:
            portfolios[index] = _record_from_portfolio(portfolio)
            break
    utils.save_portfolios(portfolios)
