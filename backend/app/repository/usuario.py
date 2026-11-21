from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


def get_by_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def get_by_email(db: Session, email: str) -> Usuario | None:
    stmt = select(Usuario).where(Usuario.email == email.lower())
    return db.execute(stmt).scalar_one_or_none()


def get_by_google_sub(db: Session, google_sub: str) -> Usuario | None:
    stmt = select(Usuario).where(Usuario.google_sub == google_sub)
    return db.execute(stmt).scalar_one_or_none()


def list_usuarios(db: Session, skip: int = 0, limit: int = 100) -> list[Usuario]:
    stmt = select(Usuario).offset(skip).limit(limit).order_by(Usuario.id)
    return list(db.execute(stmt).scalars().all())


def create(db: Session, usuario: Usuario) -> Usuario:
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def update(db: Session, usuario: Usuario) -> Usuario:
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def set_google_data(
    db: Session, usuario: Usuario, google_sub: str, nombre: str | None, foto_url: str | None
) -> Usuario:
    usuario.google_sub = google_sub
    if nombre:
        usuario.nombre = nombre
    if foto_url:
        usuario.foto_url = foto_url
    usuario.email_verificado = True
    return update(db, usuario)


def touch_ultimo_acceso(db: Session, usuario: Usuario) -> Usuario:
    usuario.ultimo_acceso = datetime.now(timezone.utc)
    return update(db, usuario)
