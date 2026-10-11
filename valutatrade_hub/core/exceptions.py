"""Пользовательские исключения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовое исключение проекта.

    Позволяет в CLI ловить все доменные ошибки одним except.
    """


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств на кошельке.

    Текст сообщения задан в ТЗ 3.2 дословно; значения выводятся
    с четырьмя знаками после запятой, как в примерах ТЗ.
    """

    def __init__(self, available: float, required: float, code: str) -> None:
        """Создаёт исключение с деталями по доступному и требуемому объёму.

        Args:
            available: доступный баланс.
            required: требуемая сумма.
            code: код валюты.
        """
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта.

    Бросается фабрикой get_currency() и при валидации входа в get-rate.
    """

    def __init__(self, code: str) -> None:
        """Создаёт исключение для неизвестного кода валюты.

        Args:
            code: неизвестный код валюты.
        """
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Сбой внешнего API (Parser Service или поставщик курсов)."""

    def __init__(self, reason: str) -> None:
        """Создаёт исключение с причиной сбоя обращения к API.

        Args:
            reason: описание причины сбоя.
        """
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
