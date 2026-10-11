"""Parser Service: сбор курсов из внешних источников."""

from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.updater import RatesUpdater

__all__ = ["ParserConfig", "RatesUpdater"]
