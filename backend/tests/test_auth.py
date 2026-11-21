from app.core.security import crear_jwt
from app.models.usuario import RolUsuario
from tests.conftest import create_user


def _google_payload(email: str, *, sub: str = "google-sub-1", verified: bool = True):
    return {
        "sub": sub,
        "email": email,
        "email_verified": verified,
        "name": "Google Name",
        "picture": "https://example.com/photo.png",
    }


def test_login_usuario_registrado_activo(client, db_session, monkeypatch):
    user = create_user(db_session, email="user@example.com", activo=True)
    monkeypatch.setattr("app.services.auth.verificar_google_id_token", lambda _: _google_payload("user@example.com"))

    res = client.post("/auth/google", json={"id_token": "valid-token"})

    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["usuario"]["email"] == "user@example.com"
    assert "google_sub" not in body["usuario"]
    db_session.refresh(user)
    assert user.ultimo_acceso is not None


def test_login_email_no_registrado(client, monkeypatch):
    monkeypatch.setattr("app.services.auth.verificar_google_id_token", lambda _: _google_payload("nope@example.com"))

    res = client.post("/auth/google", json={"id_token": "valid-token"})

    assert res.status_code == 403


def test_login_usuario_inactivo(client, db_session, monkeypatch):
    create_user(db_session, email="inactive@example.com", activo=False)
    monkeypatch.setattr("app.services.auth.verificar_google_id_token", lambda _: _google_payload("inactive@example.com"))

    res = client.post("/auth/google", json={"id_token": "valid-token"})

    assert res.status_code == 403


def test_login_email_no_verificado(client, db_session, monkeypatch):
    create_user(db_session, email="unverified@example.com", activo=True)
    monkeypatch.setattr(
        "app.services.auth.verificar_google_id_token",
        lambda _: _google_payload("unverified@example.com", verified=False),
    )

    res = client.post("/auth/google", json={"id_token": "valid-token"})

    assert res.status_code == 401


def test_primer_login_completa_google_sub(client, db_session, monkeypatch):
    user = create_user(db_session, email="first@example.com", activo=True, google_sub=None)
    monkeypatch.setattr(
        "app.services.auth.verificar_google_id_token",
        lambda _: _google_payload("first@example.com", sub="sub-first-123"),
    )

    res = client.post("/auth/google", json={"id_token": "valid-token"})

    assert res.status_code == 200
    db_session.refresh(user)
    assert user.google_sub == "sub-first-123"
    assert user.nombre == "Google Name"
    assert user.foto_url == "https://example.com/photo.png"
    assert user.email_verificado is True


def test_get_usuarios_rol_usuario_403(client, db_session):
    user = create_user(db_session, email="u@example.com", rol=RolUsuario.USUARIO)
    token = crear_jwt(user.id, user.rol)

    res = client.get("/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 403


def test_get_usuarios_rol_admin_200(client, db_session):
    admin = create_user(db_session, email="admin@example.com", rol=RolUsuario.ADMIN)
    token = crear_jwt(admin.id, admin.rol)

    res = client.get("/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert any(u["email"] == "admin@example.com" for u in res.json())
