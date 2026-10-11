from __future__ import annotations

import hashlib
import secrets
from copy import deepcopy
from datetime import datetime
from typing import Any


class User:
    """Класс пользователя системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime | str,
    ) -> None:
        self._user_id: int = user_id

        # Валидация username
        self._validate_username(username)
        self._username: str = username

        self._salt: str = salt
        self._hashed_password: str = hashed_password

        if isinstance(registration_date, str):
            self._registration_date: datetime = datetime.fromisoformat(
                registration_date
            )
        else:
            self._registration_date = registration_date

    @staticmethod
    def _validate_username(username: str) -> None:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")

    @staticmethod
    def _validate_password_length(password: str) -> None:
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Хеширование пароля: SHA-256(password + salt)."""
        combined = (password + salt).encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> User:
        """Фабричный метод для создания нового пользователя с генерацией соли."""
        cls._validate_username(username)
        cls._validate_password_length(password)

        salt = secrets.token_hex(4)  # генерация случайной соли
        hashed_password = cls._hash_password(password, salt)
        reg_date = datetime.now()

        return cls(
            user_id=user_id,
            username=username.strip(),
            hashed_password=hashed_password,
            salt=salt,
            registration_date=reg_date,
        )

    # --- Геттеры и сеттеры ---

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, new_username: str) -> None:
        self._validate_username(new_username)
        self._username = new_username.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # --- Методы класса ---

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение с сохранённым хешем."""
        computed_hash = self._hash_password(password, self._salt)
        return secrets.compare_digest(self._hashed_password, computed_hash)

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя с обновлением хеша и соли."""
        self._validate_password_length(new_password)
        self._salt = secrets.token_hex(4)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def get_user_info(self) -> dict[str, Any]:
        """Возвращает информацию о пользователе (без конфиденциальных полей)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в формат users.json."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }


class Wallet:
    """Кошелёк пользователя для конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code: str = currency_code.strip().upper()
        self._balance: float = 0.0
        self.balance = balance  # вызов сеттера с валидацией

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Запрещает отрицательные значения и некорректные типы."""
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополнение баланса."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self._balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снятие средств."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount > self._balance:
            available = f"{self._balance:.4f} {self.currency_code}"
            required = f"{amount:.4f} {self.currency_code}"
            raise ValueError(
                f"Недостаточно средств: доступно {available}, требуется {required}"
            )
        self._balance -= float(amount)

    def get_balance_info(self) -> str:
        """Вывод информации о текущем балансе."""
        return f"{self.currency_code}: {self._balance:.4f}"

    def to_dict(self) -> dict[str, Any]:
        """Сериализация кошелька."""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }


class Portfolio:
    """Портфель пользователя, управляющий набором кошельков."""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        self._user_id: int = user_id
        self._wallets: dict[str, Wallet] = wallets if wallets is not None else {}
        self._user: User | None = user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User | None:
        """Объект пользователя (без возможности перезаписи)."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает защищённую копию словаря кошельков."""
        return deepcopy(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        """Создаёт и добавляет новый кошелёк, если его ещё нет."""
        code = currency_code.strip().upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк для валюты '{code}' уже существует")

        new_wallet = Wallet(currency_code=code, balance=0.0)
        self._wallets[code] = new_wallet
        return new_wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает объект Wallet по коду валюты."""
        code = currency_code.strip().upper()
        if code not in self._wallets:
            raise KeyError(
                f"У вас нет кошелька '{code}'. Добавьте валюту: "
                "она создаётся автоматически при первой покупке."
            )
        return self._wallets[code]

    def get_total_value(
        self,
        base_currency: str = "USD",
        rates: dict[str, float] | None = None,
    ) -> float:
        """Конвертирует балансы всех кошельков в базовую валюту."""
        base = base_currency.strip().upper()

        # Базовые курсы-заглушки (если не передан внешний словарь)
        exchange_rates = {
            "USD": 1.0,
            "EUR": 1.0786,
            "BTC": 59337.21,
            "RUB": 0.01016,
            "ETH": 3720.0,
        }
        if rates:
            exchange_rates.update(rates)

        if base not in exchange_rates:
            raise ValueError(f"Неизвестная базовая валюта '{base}'")

        base_to_usd = exchange_rates[base]
        total_in_base = 0.0

        for code, wallet in self._wallets.items():
            if wallet.balance == 0.0:
                continue
            if code not in exchange_rates:
                raise ValueError(f"Не удалось получить курс для {code}→{base}")

            # Перевод: валюта -> USD -> base
            currency_to_usd = exchange_rates[code]
            value_in_usd = wallet.balance * currency_to_usd
            value_in_base = value_in_usd / base_to_usd
            total_in_base += value_in_base

        return total_in_base

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в формат portfolios.json."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }
