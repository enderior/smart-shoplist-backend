from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# Настройка хеширования паролей (bcrypt — надёжный алгоритм)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Настройки JWT из .env файла
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


# --- Хеширование паролей ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, совпадает ли введённый пароль с хешем из базы данных."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Превращает пароль в безопасный хеш (bcrypt)."""
    return pwd_context.hash(password)


# --- JWT токены ---
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Создаёт JWT-токен с данными пользователя и временем жизни."""
    to_encode = data.copy()

    # Устанавливаем, когда токен протухнет
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Кодируем и подписываем токен нашим секретным ключом
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """Декодирует JWT-токен и проверяет его подпись."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None