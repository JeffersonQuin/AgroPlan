export type UnitSystem = 'metric' | 'imperial';

export type ProjectStatus = 'completed' | 'in_progress';

export type ProjectFilter = 'all' | ProjectStatus;

export type ProjectSort = 'recent' | 'area_desc' | 'name';

/** A crop block drawn inside the parcel preview. */
export interface CropSlice {
  name: string;
  areaM2: number;
  /** SVG fill for the block; the design system green/tan palette. */
  color: string;
}

/** Next action offered by a project card. */
export interface ProjectNextStep {
  label: string;
  icon: string;
  /** Wizard step the action resumes, when the project is still in progress. */
  step?: number;
}

export interface Project {
  id: string;
  name: string;
  location: string;
  /** ISO local timestamp, formatted for display by `formatModifiedAt`. */
  modifiedAt: string;
  status: ProjectStatus;
  statusLabel: string;
  statusIcon: string;
  unitSystem: UnitSystem;
  areaM2: number;
  /** Number of irrigation sectors, or null when not designed yet. */
  sectors: number | null;
  sectorsLabel: string;
  speciesLabel: string;
  hydraulicSpecs: string;
  crops: CropSlice[];
  parcelShape: 'rectangle' | 'trapezoid';
  nextStep: ProjectNextStep;
  /** True for the reference project that shows the "verified" badge. */
  verified?: boolean;
}

export interface CreateProjectInput {
  name: string;
  location: string;
  unitSystem: UnitSystem;
}
