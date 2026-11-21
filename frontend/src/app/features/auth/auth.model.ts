/** Which panel of the authentication screen is active. */
export type AuthMode = 'login' | 'register';

/** Lifecycle of a submit attempt. */
export type AuthStatus = 'idle' | 'submitting' | 'success';

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

export const AUTH_COPY: Record<AuthMode, AuthCopy> = {
  login: {
    title: 'Bienvenido de nuevo',
    subtitle:
      'Ingresa tus credenciales para acceder a tus parcelas y proyectos agronómicos.',
    submit: 'Iniciar Sesión en AgroPlan',
    submitting: 'Verificando estación…',
    success: 'Acceso Autorizado',
  },
  register: {
    title: 'Crea tu cuenta técnica',
    subtitle:
      'Configura tu estación y comienza a proyectar sistemas de riego y topografía.',
    submit: 'Registrarse y Crear Espacio',
    submitting: 'Creando espacio de trabajo…',
    success: 'Espacio Creado',
  },
};

export const EMPTY_AUTH_FORM: AuthFormModel = {
  fullName: '',
  email: '',
  password: '',
  rememberStation: true,
};

/**
 * Prefilled values for the jury demo shortcut.
 * These are inert literals: nothing is verified and no session is created.
 */
export const DEMO_CREDENTIALS = {
  email: 'jurado.evaluador@agroplan.io',
  password: 'JuradoPrecision2025!',
} as const;
