/** Lifecycle of a sign-in attempt. */
export type AuthStatus = 'idle' | 'submitting' | 'success' | 'error';

/** Usuario as returned by the FastAPI backend. */
export interface BackendUser {
  id: number;
  email: string;
  nombre: string | null;
  foto_url: string | null;
  rol: string;
  activo: boolean;
  ultimo_acceso: string | null;
}

/** Response of POST /auth/google, POST /auth/login and POST /auth/register. */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  usuario: BackendUser;
}

/**
 * Email/password contract agreed with the FastAPI backend.
 *
 * The backend still only exposes `POST /auth/google` and
 * `POST /auth/google/register`, so these two endpoints are the contract the
 * frontend already speaks (the screens stay usable the day the backend lands):
 *
 *   POST /auth/login     { email, password }
 *     -> 200 TokenResponse | 401 { detail } | 422 { detail }
 *   POST /auth/register  { nombre, email, password, rol }
 *     -> 201 TokenResponse | 409 { detail } | 422 { detail }
 *
 * Both answer with the same `TokenResponse` the Google flow uses, so the store
 * persists the session the same way for all three paths.
 */
export interface EmailCredentials {
  email: string;
  password: string;
}

/** Payload of POST /auth/register. */
export interface RegisterPayload extends EmailCredentials {
  nombre: string;
  rol: string;
}

export interface AuthFormModel {
  fullName: string;
  email: string;
  password: string;
  rememberStation: boolean;
}

export interface AuthCopy {
  title: string;
  subtitle: string;
  submit: string;
  submitting: string;
  success: string;
}

export const LOGIN_COPY: AuthCopy = {
  title: 'Bienvenido de nuevo',
  subtitle:
    'Ingresá con tu cuenta de Google o, si ya tenés una cuenta con correo, con tu contraseña.',
  submit: 'Iniciar Sesión con Google',
  submitting: 'Verificando cuenta…',
  success: 'Acceso Autorizado',
};

export const EMPTY_AUTH_FORM: AuthFormModel = {
  fullName: '',
  email: '',
  password: '',
  rememberStation: true,
};

export const SESSION_STORAGE_KEY = 'agroplan.session';
