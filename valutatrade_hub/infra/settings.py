"""Singleton-загрузчик конфигурации"""

import os

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - для Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


# Значения по умолчанию: используются, если ключа нет в pyproject.toml.
_DEFAULTS: dict = {
    "data_dir": "data",
    "users_file": "data/users.json",
    "portfolios_file": "data/portfolios.json",
    "rates_file": "data/rates.json",
    "rates_ttl_seconds": 300,
    "base_currency": "USD",
    "log_file": "logs/actions.log",
    "log_format": "text",
    "log_level": "INFO",
    "starting_usd_balance": 10_000.0,
}


class SettingsLoader:
    """Единственная точка доступа к конфигурации проекта.

    Реализован через __new__: для двух независимых синглтонов
    без общей логики создания метакласс избыточен. __new__
    читабельнее и не создаёт дополнительной сущности; кеш
    экземпляра в атрибуте класса исключает повторную инициализацию
    при повторных импортах.
    """

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        """Возвращает единственный экземпляр класса."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._settings = {}
            instance._load()
            cls._instance = instance
        return cls._instance

    def _load(self) -> None:
        """Загружает настройки из pyproject.toml поверх значений по умолчанию."""
        self._settings = dict(_DEFAULTS)
        config = self._read_pyproject()
        section = config.get("tool", {}).get("valutatrade", {})
        for key, value in section.items():
            self._settings[key] = value

    @staticmethod
    def _read_pyproject() -> dict:
        """Читает pyproject.toml из корня проекта, если он есть."""
        path = "pyproject.toml"
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "rb") as file:
                return tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    def get(self, key: str, default=None):
        """Возвращает значение настройки по ключу.

        Args:
            key: имя настройки.
            default: значение, если ключ не найден (по умолчанию None).

        Returns:
            Значение настройки.
        """
        return self._settings.get(key, default)

    def reload(self) -> None:
        """Перечитывает конфигурацию (например, после правки pyproject.toml)."""
        self._load()

    @property
    def all(self) -> dict:
        """Возвращает копию всех настроек."""
        return dict(self._settings)


def get_settings() -> SettingsLoader:
    """Удобная функция-фабрика для получения синглтона настроек."""
    return SettingsLoader()
