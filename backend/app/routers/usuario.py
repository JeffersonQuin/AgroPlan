from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import usuario as usuario_service
from app.services.usuario import UsuarioServiceError

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me", response_model=UsuarioOut)
def me(current_user: Usuario = Depends(get_current_user)) -> UsuarioOut:
    return UsuarioOut.model_validate(current_user)


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_role(RolUsuario.ADMIN.value)),
) -> list[UsuarioOut]:
    usuarios = usuario_service.list_usuarios(db, skip=skip, limit=limit)
    return [UsuarioOut.model_validate(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_role(RolUsuario.ADMIN.value)),
) -> UsuarioOut:
    try:
        usuario = usuario_service.get_usuario(db, usuario_id)
    except UsuarioServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return UsuarioOut.model_validate(usuario)


@router.post("", response_model=UsuarioOut, status_code=201)
def crear_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_role(RolUsuario.ADMIN.value)),
) -> UsuarioOut:
    try:
        usuario = usuario_service.create_usuario(db, payload)
    except UsuarioServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return UsuarioOut.model_validate(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(RolUsuario.ADMIN.value)),
) -> UsuarioOut:
    try:
        usuario = usuario_service.update_usuario(db, usuario_id, payload, current_user)
    except UsuarioServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return UsuarioOut.model_validate(usuario)
