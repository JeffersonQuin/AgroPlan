from sqlalchemy.orm import Session

from app.models.usuario import RolUsuario, Usuario
from app.repository import usuario as usuario_repo
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


class UsuarioServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def list_usuarios(db: Session, skip: int = 0, limit: int = 100) -> list[Usuario]:
    return usuario_repo.list_usuarios(db, skip=skip, limit=limit)


def get_usuario(db: Session, usuario_id: int) -> Usuario:
    usuario = usuario_repo.get_by_id(db, usuario_id)
    if usuario is None:
        raise UsuarioServiceError(404, "Usuario no encontrado")
    return usuario


def create_usuario(db: Session, data: UsuarioCreate) -> Usuario:
    email = data.email.lower().strip()
    existing = usuario_repo.get_by_email(db, email)
    if existing is not None:
        raise UsuarioServiceError(409, "El email ya está registrado")

    usuario = Usuario(
        email=email,
        nombre=data.nombre,
        rol=data.rol.value if isinstance(data.rol, RolUsuario) else str(data.rol),
        activo=True,
        email_verificado=False,
    )
    return usuario_repo.create(db, usuario)


def _count_active_admins(db: Session) -> int:
    return sum(
        1
        for u in usuario_repo.list_usuarios(db, skip=0, limit=10_000)
        if u.rol == RolUsuario.ADMIN.value and u.activo
    )


def update_usuario(
    db: Session, usuario_id: int, data: UsuarioUpdate, current_user: Usuario
) -> Usuario:
    usuario = get_usuario(db, usuario_id)
    updates = data.model_dump(exclude_unset=True)

    if usuario.id == current_user.id:
        if updates.get("activo") is False:
            raise UsuarioServiceError(400, "No puedes desactivarte a ti mismo")
        new_rol = updates.get("rol")
        if new_rol is not None:
            new_rol_val = new_rol.value if isinstance(new_rol, RolUsuario) else str(new_rol)
            if new_rol_val != RolUsuario.ADMIN.value and _count_active_admins(db) <= 1:
                raise UsuarioServiceError(400, "No puedes quitarte el rol de admin si eres el último admin")

    if "nombre" in updates:
        usuario.nombre = updates["nombre"]
    if "rol" in updates and updates["rol"] is not None:
        rol = updates["rol"]
        usuario.rol = rol.value if isinstance(rol, RolUsuario) else str(rol)
    if "activo" in updates and updates["activo"] is not None:
        if (
            usuario.activo
            and updates["activo"] is False
            and usuario.rol == RolUsuario.ADMIN.value
            and _count_active_admins(db) <= 1
        ):
            raise UsuarioServiceError(400, "No se puede desactivar al último admin activo")
        usuario.activo = updates["activo"]

    return usuario_repo.update(db, usuario)
