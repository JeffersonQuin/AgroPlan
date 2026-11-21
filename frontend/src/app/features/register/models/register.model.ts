/** Agronomic profile shown in the register screen selector. */
export type UserRole =
  | 'agronomo'
  | 'productor'
  | 'instalador'
  | 'estudiante'
  | 'investigador';

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
