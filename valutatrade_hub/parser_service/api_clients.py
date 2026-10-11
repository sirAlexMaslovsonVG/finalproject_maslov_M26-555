"""API-клиенты Parser Service.

Изолируют работу с внешними API и приводят ответы
к единому формату: {"BTC_USD": 59337.21, ...}.
"""

import logging
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger("valutatrade")


class BaseApiClient(ABC):
    """Базовый клиент источника курсов."""

    name: str = "base"

    def __init__(self, config: ParserConfig) -> None:
        """Сохраняет конфигурацию.

        Args:
            config: настройки Parser Service.
        """
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict:
        """Получает курсы и приводит их к формату {pair: rate}.

        Returns:
            Словарь вида {'BTC_USD': 59337.21, 'ETH_USD': 3720.0}.

        Raises:
            ApiRequestError: при сбое источника.
        """
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko: криптовалюты против USD."""

    name = "CoinGecko"

    def fetch_rates(self) -> dict:
        """Запрашивает цены криптовалют из CoinGecko.

        Returns:
            Словарь пар '<CODE>_USD' → rate.

        Raises:
            ApiRequestError: при таймауте, сетевой ошибке или статусе 4xx/5xx.
        """
        ids = [
            self.config.CRYPTO_ID_MAP[code]
            for code in self.config.CRYPTO_CURRENCIES
            if code in self.config.CRYPTO_ID_MAP
        ]
        if not ids:
            return {}

        params = {
            "ids": ",".join(ids),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        payload = self._get(
            self.config.COINGECKO_URL,
            params=params,
            headers={},
        )

        result = {}
        for code in self.config.CRYPTO_CURRENCIES:
            api_id = self.config.CRYPTO_ID_MAP.get(code)
            if not api_id:
                continue
            entry = payload.get(api_id)
            if isinstance(entry, dict) and "usd" in entry:
                result[f"{code}_{self.config.BASE_CURRENCY}"] = float(entry["usd"])
        return result

    def _get(self, url: str, params: dict, headers: dict) -> dict:
        """Обёртка над _safe_get (единая обработка ошибок)."""
        return _safe_get(
            url,
            params=params,
            headers=headers,
            source=self.name,
            timeout=self.config.REQUEST_TIMEOUT,
        )


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API: фиатные валюты против USD."""

    name = "ExchangeRate-API"

    def fetch_rates(self) -> dict:
        """Запрашивает курсы фиатных валют из ExchangeRate-API.

        Returns:
            Словарь пар '<CODE>_USD' → rate.

        Raises:
            ApiRequestError: при отсутствии ключа, таймауте,
                сетевой ошибке, статусе 401/429 и т.п.
        """
        api_key = self.config.EXCHANGERATE_API_KEY
        if not api_key:
            raise ApiRequestError("не задан ключ EXCHANGERATE_API_KEY")

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{api_key}/latest/{self.config.BASE_CURRENCY}"
        )
        payload = _safe_get(
            url,
            params={},
            headers={},
            source=self.name,
            timeout=self.config.REQUEST_TIMEOUT,
        )

        conversions = payload.get("conversion_rates", {})
        result = {}
        for code in self.config.FIAT_CURRENCIES:
            rate = conversions.get(code)
            if not rate:
                continue
            # API отдаёт USD -> CODE; нам нужно CODE -> USD.
            result[f"{code}_{self.config.BASE_CURRENCY}"] = round(1.0 / float(rate), 8)
        return result


def _safe_get(url: str, params: dict, headers: dict, source: str, timeout: int) -> dict:
    """GET-запрос с обработкой сетевых ошибок и HTTP-статусов.

    Args:
        url: адрес запроса.
        params: query-параметры.
        headers: HTTP-заголовки.
        source: имя источника для сообщений.
        timeout: таймаут запроса в секундах.

    Returns:
        Разобранный JSON-ответ.

    Raises:
        ApiRequestError: при таймауте, сетевой ошибке, некорректном JSON
            или HTTP-статусе ошибки.
    """
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout as error:
        raise ApiRequestError(f"{source}: превышен таймаут запроса") from error
    except requests.exceptions.RequestException as error:
        raise ApiRequestError(f"{source}: сетевая ошибка ({error})") from error

    if response.status_code == 401:
        raise ApiRequestError(f"{source}: неверный или отсутствующий API-ключ (401)")
    if response.status_code == 429:
        raise ApiRequestError(f"{source}: превышен лимит запросов (429)")
    if response.status_code >= 400:
        raise ApiRequestError(f"{source}: HTTP {response.status_code}")

    try:
        return response.json()
    except ValueError as error:
        raise ApiRequestError(f"{source}: некорректный JSON в ответе") from error
