"""Бизнес-логика ValutaTrade Hub."""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core import utils
from valutatrade_hub.core.currencies import get_currency, is_fiat
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User, Wallet

# --- Текущая сессия (в памяти процесса) ---
_current_user: User | None = None


def get_current_user() -> User | None:
    """Возвращает текущего залогиненного пользователя или None."""
    return _current_user


def logout() -> None:
    """Завершает сессию текущего пользователя."""
    global _current_user
    _current_user = None


def _require_login() -> User:
    """Возвращает залогиненного пользователя или бросает PermissionError."""
    if _current_user is None:
        raise PermissionError("Сначала выполните login")
    return _current_user


# --- Сборка объектов User ---


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
    """Возвращает следующий свободный user_id (автоинкремент)."""
    if not users:
        return 1
    return max(record["user_id"] for record in users) + 1


# --- Сборка объектов Portfolio ---


def _ensure_starting_usd(record: dict) -> dict:
    """Гарантирует наличие USD-кошелька в записи портфеля.

    Нужно для совместимости с портфелями, созданными до введения
    стартового баланса (ТЗ 3.5: безопасные операции чтение→модификация→запись).

    Args:
        record: запись портфеля из portfolios.json.

    Returns:
        Та же запись с гарантированно присутствующим USD-кошельком.
    """
    wallets = record.setdefault("wallets", {})
    if "USD" not in wallets:
        wallets["USD"] = {
            "currency_code": "USD",
            "balance": utils.STARTING_USD_BALANCE,
        }
    return record


def _portfolio_from_record(record: dict, user: User) -> Portfolio:
    """Преобразует запись из portfolios.json в объект Portfolio."""
    wallets = {}
    for code, data in record.get("wallets", {}).items():
        wallets[code] = Wallet(
            currency_code=data.get("currency_code", code),
            balance=data.get("balance", 0.0),
        )
    return Portfolio(user_id=record["user_id"], user=user, wallets=wallets)


def _record_from_portfolio(portfolio: Portfolio) -> dict:
    """Преобразует объект Portfolio в словарь для portfolios.json."""
    return {
        "user_id": portfolio.user_id,
        "wallets": {
            code: {"currency_code": wallet.currency_code, "balance": wallet.balance}
            for code, wallet in portfolio.wallets.items()
        },
    }


def _find_portfolio_record(portfolios: list, user_id: int) -> dict:
    """Находит запись портфеля по user_id."""
    for record in portfolios:
        if record["user_id"] == user_id:
            return record
    raise KeyError(f"Портфель пользователя id={user_id} не найден")


def _save_portfolio(portfolio: Portfolio, portfolios: list) -> None:
    """Записывает изменённый портфель обратно в portfolios.json."""
    for index, record in enumerate(portfolios):
        if record["user_id"] == portfolio.user_id:
            portfolios[index] = _record_from_portfolio(portfolio)
            break
    utils.save_portfolios(portfolios)


def _load_portfolio() -> tuple[Portfolio, list]:
    """Загружает портфель текущего пользователя и список всех портфелей."""
    user = _require_login()
    portfolios = utils.load_portfolios()
    record = _find_portfolio_record(portfolios, user.user_id)
    record = _ensure_starting_usd(record)
    return _portfolio_from_record(record, user), portfolios


# --- Валидация валют ---


def _validate_known_currency(currency: str) -> str:
    """Проверяет код через реестр и возвращает нормализованный код.

    Raises:
        CurrencyNotFoundError: если код неизвестен.
    """
    code = utils.validate_currency_code(currency)
    get_currency(code)
    return code


# --- Команда register ---


def register(
    username: str, password: str, starting_balance: float | None = None
) -> str:
    """Создаёт нового пользователя и стартовый портфель.

    Args:
        username: имя пользователя (не пустое, уникальное).
        password: пароль (не короче 4 символов).
        starting_balance: стартовый баланс USD; если None — берётся из utils.

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

    balance = (
        utils.STARTING_USD_BALANCE if starting_balance is None else starting_balance
    )
    portfolios = utils.load_portfolios()
    portfolios.append(
        {
            "user_id": user_id,
            "wallets": {
                "USD": {"currency_code": "USD", "balance": balance},
            },
        }
    )
    utils.save_portfolios(portfolios)

    return (
        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


# --- Команда login ---


def login(username: str, password: str) -> str:
    """Входит в систему и фиксирует текущую сессию."""
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


# --- Конвертация курсов ---


def _rate_to_base(currency: str, base: str, rates: dict) -> float:
    """Возвращает курс currency → base по кешу rates.json.

    Поддерживает прямой курс, обратный и расчёт через USD.

    Raises:
        ApiRequestError: если курс недоступен.
    """
    if currency == base:
        return 1.0

    direct = f"{currency}_{base}"
    if direct in rates:
        return rates[direct]["rate"]

    reverse = f"{base}_{currency}"
    if reverse in rates and rates[reverse]["rate"]:
        return 1.0 / rates[reverse]["rate"]

    to_usd = f"{currency}_USD"
    base_usd = f"{base}_USD"
    if to_usd in rates and base_usd in rates and rates[base_usd]["rate"]:
        return rates[to_usd]["rate"] / rates[base_usd]["rate"]

    raise ApiRequestError(f"курс {currency}->{base} недоступен")


# --- Команда show-portfolio ---


def show_portfolio(base_currency: str = "USD") -> dict:
    """Считает портфель пользователя в базовой валюте.

    Raises:
        PermissionError: если пользователь не залогинен.
        CurrencyNotFoundError: если базовая валюта неизвестна.
    """
    user = _require_login()
    base = _validate_known_currency(base_currency)

    rates = utils.refresh_rates()

    portfolios = utils.load_portfolios()
    record = _find_portfolio_record(portfolios, user.user_id)
    record = _ensure_starting_usd(record)
    portfolio = _portfolio_from_record(record, user)

    wallets_info = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        rate = _rate_to_base(code, base, rates)
        value = wallet.balance * rate
        total += value
        wallets_info.append(
            {
                "currency": code,
                "balance": wallet.balance,
                "value": value,
                "is_fiat": is_fiat(code),
            }
        )

    return {
        "user": user.username,
        "base": base,
        "wallets": wallets_info,
        "total": total,
    }


# --- Команды buy / sell ---


def _debit_usd(portfolio: Portfolio, cost: float, code: str) -> None:
    """Списывает USD за покупку валюты.

    Raises:
        InsufficientFundsError: если на USD-кошельке не хватает средств.
    """
    if "USD" not in portfolio.wallets:
        portfolio.add_currency("USD")
    wallet = portfolio.get_wallet("USD")
    if wallet.balance < cost:
        raise InsufficientFundsError(wallet.balance, cost, "USD")
    wallet.withdraw(cost)


def _credit_usd(portfolio: Portfolio, revenue: float) -> None:
    """Начисляет USD после продажи валюты."""
    if "USD" not in portfolio.wallets:
        portfolio.add_currency("USD")
    portfolio.get_wallet("USD").deposit(revenue)


def buy(currency: str, amount) -> dict:
    """Покупает валюту: списывает USD и пополняет кошелёк валюты.

    Raises:
        PermissionError: если пользователь не залогинен.
        CurrencyNotFoundError: если валюта неизвестна.
        ValueError: если amount некорректен.
        InsufficientFundsError: если на USD-кошельке не хватает средств.
    """
    code = _validate_known_currency(currency)
    value = utils.validate_amount(amount)

    portfolio, portfolios = _load_portfolio()

    rates = utils.refresh_rates()
    rate = _rate_to_base(code, "USD", rates)
    cost = value * rate

    _debit_usd(portfolio, cost, code)

    if code not in portfolio.wallets:
        portfolio.add_currency(code)

    wallet = portfolio.get_wallet(code)
    before = wallet.balance
    wallet.deposit(value)
    after = wallet.balance

    _save_portfolio(portfolio, portfolios)

    return {
        "currency": code,
        "amount": value,
        "before": before,
        "after": after,
        "rate": rate,
        "cost": cost,
    }


def sell(currency: str, amount) -> dict:
    """Продаёт валюту: уменьшает кошелёк валюты и начисляет USD.

    Raises:
        PermissionError: если пользователь не залогинен.
        CurrencyNotFoundError: если валюта неизвестна.
        ValueError: если amount некорректен или кошелька нет.
        InsufficientFundsError: если средств недостаточно.
    """
    code = _validate_known_currency(currency)
    value = utils.validate_amount(amount)

    portfolio, portfolios = _load_portfolio()

    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )

    wallet = portfolio.get_wallet(code)
    before = wallet.balance

    rates = utils.refresh_rates()
    rate = _rate_to_base(code, "USD", rates)

    wallet.withdraw(value)
    after = wallet.balance
    revenue = value * rate

    _credit_usd(portfolio, revenue)

    _save_portfolio(portfolio, portfolios)

    return {
        "currency": code,
        "amount": value,
        "before": before,
        "after": after,
        "rate": rate,
        "revenue": revenue,
    }


# --- Команда get-rate ---


def get_rate(from_currency: str, to_currency: str) -> dict:
    """Возвращает курс обмена из валюты в валюту.

    Raises:
        PermissionError: если пользователь не залогинен.
        CurrencyNotFoundError: если код валюты неизвестен.
        ApiRequestError: если курс недоступен.
    """
    _require_login()

    source = _validate_known_currency(from_currency)
    target = _validate_known_currency(to_currency)

    rates = utils.load_rates()
    last_refresh = rates.get("last_refresh")

    if not last_refresh or not utils.is_fresh(last_refresh):
        try:
            rates = utils.refresh_rates()
        except OSError as error:
            raise ApiRequestError(str(error)) from error

    key = f"{source}_{target}"
    if key in rates:
        entry = rates[key]
        return {
            "from": source,
            "to": target,
            "rate": entry["rate"],
            "updated_at": entry["updated_at"],
            "source": rates.get("source", "неизвестно"),
        }

    rate = _rate_to_base(source, target, rates)
    return {
        "from": source,
        "to": target,
        "rate": rate,
        "updated_at": last_refresh or utils.now_iso(),
        "source": rates.get("source", "неизвестно"),
    }
