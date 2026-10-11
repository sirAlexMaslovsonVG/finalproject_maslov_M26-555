"""Доменные модели ValutaTrade Hub: User, Wallet, Portfolio."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        """Создаёт пользователя с уже захешированным паролем.

        Args:
            user_id: уникальный идентификатор.
            username: имя пользователя (не пустое).
            hashed_password: захешированный пароль.
            salt: уникальная соль пользователя.
            registration_date: дата регистрации.
        """
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя не может быть пустым")

        self._user_id: int = user_id
        self._username: str = username.strip()
        self._hashed_password: str = hashed_password
        self._salt: str = salt
        self._registration_date: datetime = registration_date

    # --- геттеры ---
    @property
    def user_id(self) -> int:
        """Идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @property
    def hashed_password(self) -> str:
        """Захешированный пароль."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата регистрации."""
        return self._registration_date

    # --- сеттер с проверкой ---
    @username.setter
    def username(self, value: str) -> None:
        """Меняет имя пользователя с проверкой на пустоту."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя не может быть пустым")
        self._username = value.strip()

    # --- методы класса ---
    def get_user_info(self) -> dict[str, Any]:
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя с хешированием нового значения."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли пароль с сохранённым хешем."""
        computed = hashlib.sha256((password + self._salt).encode("utf-8")).hexdigest()
        return computed == self._hashed_password

    def to_dict(self) -> dict[str, Any]:
        """Сериализует пользователя для users.json (ISO-дата)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }


class Wallet:
    """Кошелёк пользователя для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Создаёт кошелёк по коду валюты с начальным балансом.

        Args:
            currency_code: код валюты, например «USD», «BTC».
            balance: начальный баланс, по умолчанию 0.0.
        """
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code: str = currency_code.strip().upper()
        self._balance: float = 0.0
        self.balance = balance  # вызов сеттера с проверками

    @property
    def balance(self) -> float:
        """Текущий баланс кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс с запретом отрицательных и нечисловых значений."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс на указанную сумму."""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("'amount' должен быть положительным числом")
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self._balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снимает средства, если баланса достаточно."""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("'amount' должен быть положительным числом")
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount > self._balance:
            raise ValueError(
                f"Недостаточно средств: доступно {self._balance:.4f} "
                f"{self.currency_code}, требуется {amount:.4f} "
                f"{self.currency_code}"
            )
        self._balance -= float(amount)

    def get_balance_info(self) -> str:
        """Возвращает строку с информацией о балансе."""
        return f"{self.currency_code}: {self._balance:.4f}"

    def to_dict(self) -> dict[str, Any]:
        """Сериализует кошелёк для portfolios.json."""
        return {"currency_code": self.currency_code, "balance": self._balance}


class Portfolio:
    """Портфель пользователя: набор кошельков по кодам валют."""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        """Создаёт портфель пользователя.

        Args:
            user_id: идентификатор владельца.
            wallets: стартовый набор кошельков (по умолчанию пусто).
            user: объект пользователя для геттера `user`.
        """
        self._user_id: int = user_id
        self._wallets: dict[str, Wallet] = wallets if wallets is not None else {}
        self._user: User | None = user

    @property
    def user_id(self) -> int:
        """Идентификатор владельца портфеля."""
        return self._user_id

    @property
    def user(self) -> User | None:
        """Объект пользователя (только чтение)."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря кошельков (защита от внешних изменений)."""
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк, если такого кода ещё нет.

        Raises:
            ValueError: если кошелёк с таким кодом уже существует.
        """
        code = currency_code.strip().upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк '{code}' уже существует")
        wallet = Wallet(currency_code=code, balance=0.0)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк по коду валюты.

        Raises:
            KeyError: если кошелька с таким кодом нет.
        """
        code = currency_code.strip().upper()
        if code not in self._wallets:
            raise KeyError(f"Кошелёк '{code}' не найден")
        return self._wallets[code]

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, float] | None = None,
    ) -> float:
        """Считает суммарную стоимость всех кошельков в базовой валюте.

        Args:
            base_currency: базовая валюта (по умолчанию «USD»).
            exchange_rates: курсы вида «USD_TO», если не переданы — заглушка.
        """
        base = base_currency.strip().upper()
        rates = exchange_rates or {
            "USD": 1.0,
            "EUR": 1.0786,
            "BTC": 59337.21,
            "ETH": 3720.0,
            "RUB": 0.01016,
        }
        if base not in rates:
            raise ValueError(f"Неизвестная базовая валюта '{base}'")

        total = 0.0
        for code, wallet in self._wallets.items():
            if wallet.balance == 0.0:
                continue
            if code not in rates:
                raise ValueError(f"Курс для {code} недоступен")
            total += wallet.balance * rates[code] / rates[base]
        return total

    def to_dict(self) -> dict[str, Any]:
        """Сериализует портфель для portfolios.json."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }
