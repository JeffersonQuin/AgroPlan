from sqlalchemy.orm import Session

from app.core.security import InvalidGoogleTokenError, crear_jwt, verificar_google_id_token
from app.models.usuario import RolUsuario, Usuario
from app.repository import usuario as usuario_repo


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _validate_google_payload(id_token_str: str) -> dict:
    try:
        payload = verificar_google_id_token(id_token_str)
    except InvalidGoogleTokenError as exc:
        raise AuthError(401, "Token de Google inválido") from exc

    email_verified = payload.get("email_verified")
    if email_verified is False or email_verified == "false":
        raise AuthError(401, "El email de Google no está verificado")

    email = str(payload.get("email", "")).lower().strip()
    if not email:
        raise AuthError(401, "Token de Google inválido")
    payload["email"] = email
    return payload


def _sync_google_profile(db: Session, usuario: Usuario, payload: dict) -> Usuario:
    google_sub = payload.get("sub")
    nombre = payload.get("name")
    foto_url = payload.get("picture")
    email_verified = bool(payload.get("email_verified"))

    if not usuario.google_sub and google_sub:
        usuario = usuario_repo.set_google_data(db, usuario, str(google_sub), nombre, foto_url)
    else:
        changed = False
        if nombre and usuario.nombre != nombre:
            usuario.nombre = nombre
            changed = True
        if foto_url and usuario.foto_url != foto_url:
            usuario.foto_url = foto_url
            changed = True
        if email_verified and not usuario.email_verificado:
            usuario.email_verificado = True
            changed = True
        if changed:
            usuario = usuario_repo.update(db, usuario)
    return usuario_repo.touch_ultimo_acceso(db, usuario)


def login_with_google(db: Session, id_token_str: str) -> tuple[str, Usuario]:
    payload = _validate_google_payload(id_token_str)
    usuario = usuario_repo.get_by_email(db, payload["email"])
    if usuario is None or not usuario.activo:
        raise AuthError(403, "Usuario no autorizado")

    usuario = _sync_google_profile(db, usuario, payload)
    token = crear_jwt(usuario.id, usuario.rol)
    return token, usuario


def register_with_google(db: Session, id_token_str: str) -> tuple[str, Usuario]:
    payload = _validate_google_payload(id_token_str)
    email = payload["email"]
    google_sub = payload.get("sub")
    nombre = payload.get("name")
    foto_url = payload.get("picture")

    usuario = usuario_repo.get_by_email(db, email)
    if usuario is not None:
        if not usuario.activo:
            raise AuthError(403, "Usuario no autorizado")
        usuario = _sync_google_profile(db, usuario, payload)
        token = crear_jwt(usuario.id, usuario.rol)
        return token, usuario

    usuario = Usuario(
        email=email,
        google_sub=str(google_sub) if google_sub else None,
        nombre=nombre,
        foto_url=foto_url,
        email_verificado=bool(payload.get("email_verified")),
        rol=RolUsuario.CLIENTE.value,
        activo=True,
    )
    usuario = usuario_repo.create(db, usuario)
    usuario = usuario_repo.touch_ultimo_acceso(db, usuario)
    token = crear_jwt(usuario.id, usuario.rol)
    return token, usuario
