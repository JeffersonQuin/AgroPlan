from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings


class InvalidGoogleTokenError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


def verificar_google_id_token(token: str) -> dict[str, Any]:
    try:
        payload = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except Exception as exc:  # google-auth raises various exceptions
        raise InvalidGoogleTokenError("Token de Google inválido") from exc

    if not payload.get("email"):
        raise InvalidGoogleTokenError("Token de Google sin email")
    return payload


def crear_jwt(usuario_id: int, rol: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decodificar_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token inválido") from exc
