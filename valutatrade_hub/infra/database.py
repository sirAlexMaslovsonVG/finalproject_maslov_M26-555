"""Singleton DatabaseManager.
Абстракция над JSON-хранилищем: безопасные операции
чтение → модификация → запись с атомарной записью (tmp → rename).
"""

import json
import os

from valutatrade_hub.infra.settings import get_settings


class DatabaseManager:
    """Единая точка доступа к JSON-файлам данных.

    Реализован через __new__ по тем же причинам, что и SettingsLoader:
    простота, читабельность и отсутствие нужды в метаклассе.
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        """Возвращает единственный экземпляр класса."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._settings = get_settings()
            instance._ensure_dirs()
            cls._instance = instance
        return cls._instance

    def _ensure_dirs(self) -> None:
        """Создаёт каталоги данных и логов, если их нет."""
        os.makedirs(self._settings.get("data_dir"), exist_ok=True)
        log_dir = os.path.dirname(self._settings.get("log_file"))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    def load(self, path: str, default):
        """Читает JSON из файла; при ошибке возвращает значение по умолчанию.

        Args:
            path: путь к JSON-файлу.
            default: значение, если файл отсутствует или повреждён.

        Returns:
            Данные из файла либо default.
        """
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return default

    def save(self, path: str, data) -> None:
        """Атомарно сохраняет данные в JSON-файл (tmp → rename).

        Args:
            path: путь к JSON-файлу.
            data: сериализуемые данные.
        """
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    # --- Удобные обёртки над конкретными файлами ---

    def load_users(self) -> list:
        """Читает пользователей из users.json."""
        return self.load(self._settings.get("users_file"), [])

    def save_users(self, users: list) -> None:
        """Сохраняет пользователей в users.json."""
        self.save(self._settings.get("users_file"), users)

    def load_portfolios(self) -> list:
        """Читает портфели из portfolios.json."""
        return self.load(self._settings.get("portfolios_file"), [])

    def save_portfolios(self, portfolios: list) -> None:
        """Сохраняет портфели в portfolios.json."""
        self.save(self._settings.get("portfolios_file"), portfolios)

    def load_rates(self) -> dict:
        """Читает кеш курсов из rates.json."""
        return self.load(self._settings.get("rates_file"), {})

    def save_rates(self, rates: dict) -> None:
        """Сохраняет кеш курсов в rates.json."""
        self.save(self._settings.get("rates_file"), rates)


def get_database() -> DatabaseManager:
    """Удобная функция-фабрика для получения синглтона БД."""
    return DatabaseManager()
