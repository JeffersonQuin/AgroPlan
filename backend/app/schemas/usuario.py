from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.usuario import RolUsuario


class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: str | None = None


class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre: str | None = None
    rol: RolUsuario = RolUsuario.CLIENTE


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    rol: RolUsuario | None = None
    activo: bool | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre: str | None
    foto_url: str | None
    rol: RolUsuario
    activo: bool
    ultimo_acceso: datetime | None


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
