import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def create_access_token(user_identifier: str) -> str:
    """
    Создает JWT-токен с зашитым user_identifier и сроком действия 1 час.
    
    :param user_identifier: Идентификатор пользователя (например, email или никнейм).
    :return: Закодированный JWT-токен.
    """
    
    payload = {"user_identifier": user_identifier}  # используем ключ "user_identifier"
    
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token
