import { UnitSystem } from '../models/project.model';

const M2_PER_ACRE = 4046.8564224;
const M2_PER_SQFT = 0.09290304;

/** Thousands separator with a comma, as written in the reference mockups. */
export function formatThousands(value: number): string {
  const rounded = Math.round(value);
  return rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/** '2026-11-21T11:06:00' -> '21/11 11:06'. Locale-independent on purpose. */
export function formatModifiedAt(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!match) return iso;

  const [, , month, day, hour, minute] = match;
  return `${day}/${month} ${hour}:${minute}`;
}

/** '0.32 ha (3,200 m²)' or, in imperial units, '0.79 ac (34,445 ft²)'. */
export function formatArea(areaM2: number, unitSystem: UnitSystem = 'metric'): string {
  if (unitSystem === 'imperial') {
    const acres = (areaM2 / M2_PER_ACRE).toFixed(2);
    const squareFeet = formatThousands(areaM2 / M2_PER_SQFT);
    return `${acres} ac (${squareFeet} ft²)`;
  }

  const hectares = (areaM2 / 10000).toFixed(2);
  return `${hectares} ha (${formatThousands(areaM2)} m²)`;
}

/** Local 'YYYY-MM-DDTHH:mm:00' stamp, matching `formatModifiedAt`'s input. */
export function toLocalIso(date: Date): string {
  const pad = (value: number) => value.toString().padStart(2, '0');
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  return `${day}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}
