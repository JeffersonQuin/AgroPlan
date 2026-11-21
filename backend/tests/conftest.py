import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure test settings before importing app modules that read settings.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")

from app.database import Base, get_db
from app.main import app
from app.models.usuario import RolUsuario, Usuario


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def create_user(
    db: Session,
    *,
    email: str,
    rol: RolUsuario = RolUsuario.USUARIO,
    activo: bool = True,
    google_sub: str | None = None,
    nombre: str | None = "Test User",
    email_verificado: bool = False,
) -> Usuario:
    user = Usuario(
        email=email.lower(),
        rol=rol.value,
        activo=activo,
        google_sub=google_sub,
        nombre=nombre,
        email_verificado=email_verificado,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
