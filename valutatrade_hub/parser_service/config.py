"""Конфигурация Parser Service .

Все изменяемые параметры вынесены в один файл, чтобы избежать
hardcoding в логике. API-ключ загружается из переменных окружения.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ParserConfig:
    """Настройки Parser Service.

    Attributes:
        EXCHANGERATE_API_KEY: ключ ExchangeRate-API из окружения.
        COINGECKO_URL: эндпоинт CoinGecko для получения цен крипты.
        EXCHANGERATE_API_URL: базовый URL ExchangeRate-API.
        BASE_CURRENCY: базовая валюта запросов (фиат).
        FIAT_CURRENCIES: список фиатных кодов для отслеживания.
        CRYPTO_CURRENCIES: список криптокодов для отслеживания.
        CRYPTO_ID_MAP: сопоставление тикер → id CoinGecko.
        RATES_FILE_PATH: путь к кешу Core Service.
        HISTORY_FILE_PATH: путь к истории Parser Service.
        REQUEST_TIMEOUT: таймаут HTTP-запроса в секундах.
    """

    EXCHANGERATE_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
        }
    )

    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    REQUEST_TIMEOUT: int = 10
