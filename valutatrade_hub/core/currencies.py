"""Иерархия валют и реестр кодов."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактная валюта с базовыми атрибутами и поведением."""

    def __init__(self, name: str, code: str) -> None:
        """Создаёт валюту с проверкой инвариантов.

        Args:
            name: человекочитаемое имя, не пустое.
            code: код валюты; верхний регистр, 2–5 символов, без пробелов.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        if not isinstance(code, str):
            raise ValueError(f"Некорректный код валюты: {code!r}")
        code = code.strip()
        if not code.isupper() or not 2 <= len(code) <= 5 or " " in code:
            raise ValueError(
                f"Некорректный код валюты '{code}': ожидается 2–5 символов "
                "в верхнем регистре без пробелов"
            )

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление валюты для UI и логов."""

    def __repr__(self) -> str:
        """Техническое представление для отладки."""
        return f"{type(self).__name__}(code={self.code!r})"


class FiatCurrency(Currency):
    """Фиатная валюта с указанием страны или зоны эмиссии."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        """Создаёт фиатную валюту.

        Args:
            name: имя валюты.
            code: код валюты.
            issuing_country: страна или зона эмиссии.
        """
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна или зона эмиссии не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Строка вида '[FIAT] USD — US Dollar (Issuing: United States)'."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом и рыночной капитализацией."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        """Создаёт криптовалюту.

        Args:
            name: имя валюты.
            code: код валюты.
            algorithm: алгоритм консенсуса (например, «SHA-256»).
            market_cap: последняя известная капитализация.
        """
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if not isinstance(market_cap, (int, float)) or isinstance(market_cap, bool):
            raise ValueError("Капитализация должна быть числом")
        if market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной")

        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Строка вида '[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)'."""
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# --- Реестр валют (раздел 3.1 ТЗ) ---

_CURRENCIES: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russian Federation"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.05e11),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту из реестра по коду.

    Args:
        code: код валюты; регистр не важен, приводится к верхнему.

    Returns:
        Экземпляр Currency.

    Raises:
        CurrencyNotFoundError: если код неизвестен или некорректен.
    """
    if not isinstance(code, str) or not code.strip():
        raise CurrencyNotFoundError(str(code))
    normalized = code.strip().upper()
    currency = _CURRENCIES.get(normalized)
    if currency is None:
        raise CurrencyNotFoundError(normalized)
    return currency


def list_currencies() -> list[str]:
    """Возвращает отсортированный список поддерживаемых кодов валют."""
    return sorted(_CURRENCIES)


def is_fiat(code: str) -> bool:
    """Проверяет, является ли валюта фиатной (для форматирования вывода)."""
    return isinstance(get_currency(code), FiatCurrency)
