"""Иерархия валют и реестр кодов.

Раздел 3.1 ТЗ: абстрактный базовый класс Currency, наследники
FiatCurrency / CryptoCurrency, фабрика get_currency().
"""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактная валюта с базовым поведением."""

    def __init__(self, name: str, code: str) -> None:
        """Создаёт валюту с валидацией инвариантов.

        Args:
            name: человекочитаемое имя, не пустое.
            code: код валюты, верхний регистр, 2–5 символов, без пробелов.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        if not isinstance(code, str):
            raise ValueError(f"Некорректный код валюты: {code!r}")
        code = code.strip()
        if not code.isupper() or not (2 <= len(code) <= 5) or " " in code:
            raise ValueError(
                f"Некорректный код валюты '{code}': ожидается 2–5 символов "
                "в верхнем регистре без пробелов"
            )

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление валюты для UI и логов."""

    def __repr__(self) -> str:
        """Техническое представление для отладки."""
        return f"{type(self).__name__}(code={self.code!r})"


class FiatCurrency(Currency):
    """Фиатная валюта с указанием страны/зоны эмиссии."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        """Создаёт фиатную валюту.

        Args:
            name: имя валюты.
            code: код валюты.
            issuing_country: страна или зона эмиссии.
        """
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна/зона эмиссии не может быть пустой")
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
            algorithm: алгоритм (например, «SHA-256»).
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


# --- Реестр валют ---

_CURRENCIES: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russian Federation"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.05e11),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду.

    Args:
        code: код валюты (регистр не важен, но приводится к верхнему).

    Returns:
        Экземпляр Currency из реестра.

    Raises:
        CurrencyNotFoundError: если код неизвестен.
    """
    if not isinstance(code, str) or not code.strip():
        raise CurrencyNotFoundError(str(code))
    normalized = code.strip().upper()
    currency = _CURRENCIES.get(normalized)
    if currency is None:
        raise CurrencyNotFoundError(normalized)
    return currency


def list_currencies() -> list[str]:
    """Возвращает список поддерживаемых кодов валют."""
    return sorted(_CURRENCIES)
