import { Component, computed, inject } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matCheckCircleOutline,
  matErrorOutline,
  matInfoOutline,
  matVerifiedOutline,
} from '@ng-icons/material-symbols/outline';
import { WATER_SOURCE_OPTIONS, WaterSource } from '../../models/terrain.model';
import { TerrainStore } from '../../state/terrain.store';

/** The icon each validation state renders. */
const VALIDACION_ICONS = {
  ok: matCheckCircleOutline,
  warning: matErrorOutline,
} as const;

/** Right rail of the terrain step: geometry summary, validations and water. */
@Component({
  selector: 'app-terrain-summary',
  imports: [NgIcon],
  viewProviders: [
    provideIcons({
      matCheckCircleOutline,
      matErrorOutline,
      matInfoOutline,
      matVerifiedOutline,
    }),
  ],
  templateUrl: './terrain-summary.html',
})
export class TerrainSummary {
  protected readonly store = inject(TerrainStore);

  protected readonly waterOptions = WATER_SOURCE_OPTIONS;

  /** Resolves the dynamic validation state to the constant declared in `provideIcons`. */
  protected iconoValidacion(ok: boolean): string {
    return ok ? VALIDACION_ICONS.ok : VALIDACION_ICONS.warning;
  }

  protected readonly areaCalculada = computed(() =>
    Math.round(this.store.areaCalculadaM2()).toLocaleString('es-AR'),
  );

  protected waterClass(source: WaterSource): Record<string, boolean> {
    const active = this.store.waterSource() === source;
    return {
      'border-agro-500': active,
      'bg-agro-50/50': active,
      'text-agro-800': active,
      'border-slate-200': !active,
      'text-slate-700': !active,
    };
  }

  protected onWaterSource(source: WaterSource): void {
    this.store.setWaterSource(source);
  }

  /** Un campo vacío significa "no lo sé": el backend asigna el caudal. */
  protected onFlow(event: Event): void {
    this.store.setFlow(numeroOpcional(event));
  }

  protected onLevel(event: Event): void {
    this.store.setStaticLevel(numeroOpcional(event));
  }
}

/** `''` (campo vacío) se guarda como "no informado", no como cero. */
function numeroOpcional(event: Event): number | null {
  const crudo = (event.target as HTMLInputElement).value.trim();
  if (crudo === '') return null;
  const numero = Number.parseFloat(crudo);
  return Number.isFinite(numero) ? numero : null;
}
