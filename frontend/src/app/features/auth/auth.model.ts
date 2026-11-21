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

/** Response of POST /auth/google and POST /auth/google/register. */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  usuario: BackendUser;
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
    'Ingresa con tu cuenta de Google para acceder a tus parcelas y proyectos agronómicos.',
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
