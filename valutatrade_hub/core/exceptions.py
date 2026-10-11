"""Пользовательские исключения ValutaTrade Hub"""


class ValutaTradeError(Exception):
    """Базовое исключение проекта: ловится в CLI как последний рубеж."""


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств в кошельке"""

    def __init__(self, available: float, required: float, code: str) -> None:
        """Формирует сообщение о нехватке средств.

        Args:
            available: доступный баланс.
            required: требуемая сумма.
            code: код валюты.
        """
        self.available = available
        self.required = required
        self.code = code
        # Ленивый импорт: exceptions не должен тянуть currencies на этапе импорта.
        from valutatrade_hub.core.utils import format_amount

        message = (
            f"Недостаточно средств: доступно {format_amount(available, code)} {code}, "
            f"требуется {format_amount(required, code)} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестный код валюты"""

    def __init__(self, code: str) -> None:
        """Формирует сообщение о неизвестной валюте.

        Args:
            code: неизвестный код валюты.
        """
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Сбой внешнего источника курсов"""

    def __init__(self, reason: str) -> None:
        """Формирует сообщение об ошибке обращения к API.

        Args:
            reason: причина сбоя.
        """
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
