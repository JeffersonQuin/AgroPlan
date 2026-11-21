/** Agronomic profile chosen at sign-up. */
export type UserRole =
  | 'agronomo'
  | 'productor'
  | 'instalador'
  | 'estudiante'
  | 'investigador';

export type RegisterStatus = 'idle' | 'submitting' | 'success';

export interface RegisterFormModel {
  fullName: string;
  workEmail: string;
  userRole: UserRole | '';
  password: string;
  confirmPassword: string;
  termsAccepted: boolean;
}

export interface RoleOption {
  value: UserRole;
  label: string;
}

export const ROLE_OPTIONS: readonly RoleOption[] = [
  { value: 'agronomo', label: 'Ingeniero Agrónomo / Asesor Técnico' },
  { value: 'productor', label: 'Productor Agropecuario / Administrador de Finca' },
  { value: 'instalador', label: 'Instalador de Riego / Empresa de Montaje' },
  { value: 'estudiante', label: 'Estudiante Universitario / Posgrado' },
  { value: 'investigador', label: 'Investigador / Organismo de Extensión' },
];

export const EMPTY_REGISTER_FORM: RegisterFormModel = {
  fullName: '',
  workEmail: '',
  userRole: '',
  password: '',
  confirmPassword: '',
  termsAccepted: false,
};

export type RegisterSubmitLabel = 'idle' | 'submitting' | 'success';

export const REGISTER_SUBMIT_LABELS: Record<RegisterSubmitLabel, string> = {
  idle: 'Crear Cuenta y Empezar',
  submitting: 'Creando cuenta técnica…',
  success: 'Cuenta Creada',
};

export const REGISTER_MIN_PASSWORD_LENGTH = 8;
