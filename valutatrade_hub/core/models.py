"""Классы предметной области ValutaTrade Hub."""

from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError


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
        """Создаёт пользователя.

        Args:
            user_id: уникальный идентификатор.
            username: имя пользователя, не пустое.
            hashed_password: хеш пароля.
            salt: уникальная соль.
            registration_date: дата регистрации.
        """
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Возвращает имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Устанавливает имя пользователя с проверкой."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Возвращает хеш пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Возвращает соль пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Возвращает дату регистрации."""
        return self._registration_date

    def get_user_info(self) -> str:
        """Возвращает информацию о пользователе (без пароля)."""
        return (
            f"Пользователь id={self._user_id}, имя='{self._username}', "
            f"зарегистрирован: {self._registration_date.isoformat()}"
        )

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли пароль с сохранённым хешем."""
        if not isinstance(password, str):
            return False
        import hashlib

        hashed = hashlib.sha256((password + self._salt).encode("utf-8")).hexdigest()
        return hashed == self._hashed_password

    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя с новым хешированием.

        Args:
            new_password: новый пароль, не короче 4 символов.
        """
        import hashlib
        import secrets

        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._salt = secrets.token_hex(4)
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Создаёт кошелёк.

        Args:
            currency_code: код валюты (например, «USD», «BTC»).
            balance: начальный баланс, не отрицательный.
        """
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self.currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс, запрещая отрицательные и нечисловые значения."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс.

        Args:
            amount: положительная сумма пополнения.

        Raises:
            ValueError: если amount не положительное число.
        """
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("'amount' должен быть положительным числом")
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self._balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снимает средства с кошелька.

        Args:
            amount: положительная сумма снятия.

        Raises:
            ValueError: если amount не положительное число.
            InsufficientFundsError: если на балансе недостаточно средств.
        """
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("'amount' должен быть положительным числом")
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount > self._balance:
            raise InsufficientFundsError(self._balance, amount, self.currency_code)
        self._balance -= float(amount)

    def get_balance_info(self) -> str:
        """Возвращает информацию о текущем балансе."""
        return f"{self.currency_code}: баланс {self._balance:.4f}"


class Portfolio:
    """Набор кошельков одного пользователя."""

    def __init__(self, user_id: int, wallets: dict, user: User | None = None) -> None:
        """Создаёт портфель.

        Args:
            user_id: идентификатор владельца.
            wallets: словарь кошельков (ключ — код валюты).
            user: объект пользователя (для геттера user).
        """
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = dict(wallets)
        self._user = user

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор владельца портфеля."""
        return self._user_id

    @property
    def user(self) -> User | None:
        """Возвращает владельца портфеля (только для чтения)."""
        return self._user

    @property
    def wallets(self) -> dict:
        """Возвращает копию словаря кошельков."""
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк, если его ещё нет.

        Args:
            currency_code: код добавляемой валюты.

        Returns:
            Объект созданного или уже существующего кошелька.
        """
        code = currency_code.strip().upper()
        if code not in self._wallets:
            self._wallets[code] = Wallet(currency_code=code)
        return self._wallets[code]

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк по коду валюты."""
        code = currency_code.strip().upper()
        if code not in self._wallets:
            raise KeyError(f"Кошелёк '{code}' не найден")
        return self._wallets[code]

    def get_total_value(
        self, base_currency: str = "USD", rates: dict | None = None
    ) -> float:
        """Возвращает общую стоимость портфеля в базовой валюте.

        Args:
            base_currency: базовая валюта конвертации.
            rates: словарь курсов; если не задан — берётся из кеша.

        Returns:
            Общая стоимость всех кошельков в базовой валюте.
        """
        if rates is None:
            from valutatrade_hub.core import utils

            rates = utils.refresh_rates()
        from valutatrade_hub.core.usecases import _rate_to_base

        total = 0.0
        for code, wallet in self._wallets.items():
            total += wallet.balance * _rate_to_base(code, base_currency, rates)
        return total
