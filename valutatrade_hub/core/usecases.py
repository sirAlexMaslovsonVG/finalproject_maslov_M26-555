"""Бизнес-логика ValutaTrade Hub."""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core import utils
from valutatrade_hub.core.models import User

# --- Текущая сессия (в памяти процесса) ---
_current_user: User | None = None


def get_current_user() -> User | None:
    """Возвращает текущего залогиненного пользователя или None."""
    return _current_user


# --- Сборка объекта User из записи в users.json ---


def _user_from_record(record: dict) -> User:
    """Преобразует словарь из users.json в объект User."""
    return User(
        user_id=record["user_id"],
        username=record["username"],
        hashed_password=record["hashed_password"],
        salt=record["salt"],
        registration_date=datetime.fromisoformat(record["registration_date"]),
    )


def _record_from_user(user: User) -> dict:
    """Преобразует объект User в словарь для users.json."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(),
    }


def _next_user_id(users: list) -> int:
    """Автоинкремент user_id."""
    if not users:
        return 1
    return max(record["user_id"] for record in users) + 1


# --- Команда register ---


def register(username: str, password: str) -> str:
    """Создаёт нового пользователя и пустой портфель.

    Args:
        username: имя пользователя (не пустое, уникальное).
        password: пароль (не короче 4 символов).

    Returns:
        Сообщение об успешной регистрации.
    """
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    username = username.strip()

    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = utils.load_users()
    for record in users:
        if record["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = _next_user_id(users)

    salt = secrets.token_hex(4)
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    registration_date = datetime.now().replace(microsecond=0)

    user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed,
        salt=salt,
        registration_date=registration_date,
    )

    users.append(_record_from_user(user))
    utils.save_users(users)

    portfolios = utils.load_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    utils.save_portfolios(portfolios)

    return (
        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


# --- Команда login ---


def login(username: str, password: str) -> str:
    """Входит в систему и фиксирует текущую сессию.

    Args:
        username: имя пользователя.
        password: пароль.

    Returns:
        Сообщение об успешном входе.
    """
    global _current_user

    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    users = utils.load_users()
    record = None
    for item in users:
        if item["username"] == username:
            record = item
            break

    if record is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = _user_from_record(record)
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    _current_user = user
    return f"Вы вошли как '{username}'"
