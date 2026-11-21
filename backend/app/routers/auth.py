from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.schemas.usuario import GoogleLoginRequest, TokenOut, UsuarioOut
from app.services.auth import AuthError, login_with_google, register_with_google

router = APIRouter(prefix="/auth", tags=["auth"])


def _test_page_html(client_id: str) -> str:
    safe_client_id = escape(client_id, quote=True)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Prueba Login Google - AgroPlan</title>
  <script src="https://accounts.google.com/gsi/client" async defer></script>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 900px; }}
    .box {{ padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin-top: 1rem; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #f6f8fa; padding: 1rem; border-radius: 8px; }}
    .warn {{ color: #8a4b00; }}
  </style>
</head>
<body>
  <h1>Prueba de registro con Google</h1>
  <p>Esta pagina usa Google Identity Services para obtener un <code>id_token</code> y lo envia a <code>POST /auth/google/register</code>.</p>
  <p class="warn">Solo para pruebas locales. Asegura que el origen de esta pagina este autorizado en Google Cloud Console.</p>

  <div class="box">
    <div id="g_id_onload"
         data-client_id="{safe_client_id}"
         data-callback="onGoogleCredential"
         data-auto_prompt="false"></div>
    <div class="g_id_signin" data-type="standard" data-size="large" data-theme="outline" data-text="sign_in_with"></div>
  </div>

  <div class="box">
    <h3>Respuesta del backend</h3>
    <pre id="result">Aun no hay registro.</pre>
  </div>

  <script>
    async function onGoogleCredential(response) {{
      const result = document.getElementById('result');
      result.textContent = 'Enviando id_token al backend...';
      try {{
        const res = await fetch('/auth/google/register', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ id_token: response.credential }})
        }});
        const text = await res.text();
        let body;
        try {{ body = JSON.parse(text); }} catch {{ body = text; }}
        result.textContent = 'HTTP ' + res.status + '\\n' + JSON.stringify(body, null, 2);
      }} catch (err) {{
        result.textContent = 'Error de red: ' + err;
      }}
    }}
  </script>
</body>
</html>"""


@router.get("/google/test", response_class=HTMLResponse, include_in_schema=False)
def google_login_test_page(request: Request) -> HTMLResponse:
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no configurado")
    return HTMLResponse(_test_page_html(client_id))


@router.post("/google", response_model=TokenOut)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> TokenOut:
    try:
        access_token, usuario = login_with_google(db, payload.id_token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return TokenOut(access_token=access_token, usuario=UsuarioOut.model_validate(usuario))


@router.post("/google/register", response_model=TokenOut, status_code=201)
def google_register(payload: GoogleLoginRequest, db: Session = Depends(get_db)) -> TokenOut:
    try:
        access_token, usuario = register_with_google(db, payload.id_token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return TokenOut(access_token=access_token, usuario=UsuarioOut.model_validate(usuario))
