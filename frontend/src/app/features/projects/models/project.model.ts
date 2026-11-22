export type UnitSystem = 'metric' | 'imperial';

export type ProjectStatus = 'completed' | 'in_progress';

export type ProjectFilter = 'all' | ProjectStatus;

export type ProjectSort = 'recent' | 'area_desc' | 'name';

/** Which reference schematic the card draws. */
export type PreviewVariant = 'mi-parcela' | 'parcela-norte' | 'finca-el-paraiso' | 'empty';

/** A crop block listed in the card. */
export interface CropSlice {
  name: string;
  areaM2: number;
}

/** Next action offered by a project card. */
export interface ProjectNextStep {
  label: string;
  icon: string;
  /** Wizard step the action resumes, when the project is still in progress. */
  step?: number;
}

/**
 * Icons the card draws next to the project name and in its status row.
 *
 * These are the keys of the map `ProjectCard` resolves to the real `@ng-icons`
 * constants; the icons themselves are declared in that component.
 */
export type ProjectCardIcon =
  'verified' | 'pending' | 'check_circle' | 'edit_note' | 'tune' | 'settings';

export interface Project {
  id: string;
  name: string;
  location: string;
  /** ISO local timestamp, formatted for display by `formatModifiedAt`. */
  modifiedAt: string;
  status: ProjectStatus;
  statusLabel: string;
  statusIcon: ProjectCardIcon;
  /** Colour token for the status icon, e.g. text-secondary. */
  statusTone: string;
  /** Icon shown next to the project name in the card header. */
  headerIcon: ProjectCardIcon;
  /** Colour token for the header icon. */
  headerTone: string;
  /** Tooltip of the header icon. */
  headerTitle: string;
  unitSystem: UnitSystem;
  areaM2: number;
  sectorsLabel: string;
  speciesLabel: string;
  irrigationType: string;
  hydraulicSpecs: string;
  crops: CropSlice[];
  preview: PreviewVariant;
  /** Wizard step chip over the schematic, e.g. "Paso 4: Resultado". */
  stepLabel?: string;
  /** Dimension chip over the schematic, e.g. "60.00 × 40.00 m". */
  dimensionsLabel?: string;
  nextStep: ProjectNextStep;
}

export interface CreateProjectInput {
  name: string;
  location: string;
  unitSystem: UnitSystem;
}

/* -------------------------------------------------------------------------- */
/* Backend contract (FastAPI)                                                  */
/* -------------------------------------------------------------------------- */

export type EstadoProyectoApi = 'borrador' | 'en_progreso' | 'completado';

/** Item of `GET /proyectos`: only what the card draws. */
export interface ProyectoListadoApi {
  id: string;
  nombre: string;
  zona: string | null;
  unidad: UnitSystem;
  estado: EstadoProyectoApi;
  area_m2: number | null;
  cultivos_count: number;
  sistema_tipo: string | null;
  ultimo_paso_completado: number;
  actualizado_en: string;
  version: number;
}

/** `POST /proyectos` and `GET /proyectos/{id}`. */
export interface ProyectoApi {
  id: string;
  nombre: string;
  zona: string | null;
  unidad: UnitSystem;
  estado: EstadoProyectoApi;
  paso_actual: number;
  ultimo_paso_completado: number;
  version: number;
  corrida_actual_id: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface CrearProyectoApi {
  nombre: string;
  zona?: string | null;
  unidad?: UnitSystem;
}
