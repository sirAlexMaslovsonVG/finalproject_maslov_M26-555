"""Оркестратор обновления курсов Parser Service (раздел 4.4 ТЗ, п.5-6)."""

import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service import storage
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger("valutatrade")


class RatesUpdater:
    """Опрашивает источники, объединяет курсы и сохраняет их."""

    def __init__(
        self, config: ParserConfig | None = None, clients: list | None = None
    ) -> None:
        """Инициализирует оркестратор.

        Args:
            config: настройки Parser Service; если None — создаётся по умолчанию.
            clients: список клиентов; если None — оба стандартных.
        """
        self.config = config or ParserConfig()
        self.clients = (
            clients
            if clients is not None
            else [
                CoinGeckoClient(self.config),
                ExchangeRateApiClient(self.config),
            ]
        )

    def run_update(self) -> dict:
        """Выполняет один цикл обновления курсов.

        Сбой отдельного источника не прерывает обновление целиком.
        Если не удалось получить данные ни из одного источника,
        бросается ApiRequestError.

        Returns:
            Словарь {'updated': int, 'sources': {name: count}, 'errors': {name: str}}.

        Raises:
            ApiRequestError: если ни один источник не ответил.
        """
        merged = {}
        pair_sources = {}
        sources = {}
        errors = {}

        for client in self.clients:
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                logger.warning("%s: источник недоступен: %s", client.name, error)
                errors[client.name] = str(error)
                continue
            if not rates:
                errors[client.name] = "пустой ответ"
                continue

            merged.update(rates)
            for pair in rates:
                pair_sources[pair] = client.name
            sources[client.name] = len(rates)
            storage.append_history(self.config.HISTORY_FILE_PATH, rates, client.name)

        if not merged:
            raise ApiRequestError(
                "не удалось получить курсы ни из одного источника: "
                + "; ".join(f"{name}: {err}" for name, err in errors.items())
            )

        storage.save_rates(self.config.RATES_FILE_PATH, merged, pair_sources)
        logger.info("Обновлено пар: %s", len(merged))

        return {"updated": len(merged), "sources": sources, "errors": errors}
