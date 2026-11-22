import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import {
  ParcelShape,
  SHAPE_OPTIONS,
  SOIL_OPTIONS,
  SoilType,
  TerrainDimensions,
} from '../../models/terrain.model';
import { TerrainStore } from '../../state/terrain.store';

/** Left rail of the terrain step: identity, cotas, soil and slope. */
@Component({
  selector: 'app-terrain-form',
  imports: [RouterLink],
  templateUrl: './terrain-form.html',
})
export class TerrainForm {
  protected readonly store = inject(TerrainStore);

  protected readonly shapeOptions = SHAPE_OPTIONS;
  protected readonly soilOptions = SOIL_OPTIONS;

  protected shapeClass(shape: ParcelShape): Record<string, boolean> {
    const active = this.store.shape() === shape;
    return {
      'bg-white': active,
      'text-agro-700': active,
      'font-bold': active,
      'shadow-xs': active,
      border: active,
      'border-slate-200/60': active,
      'text-slate-600': !active,
      'font-semibold': !active,
      'hover:text-slate-900': !active,
    };
  }

  protected onName(event: Event): void {
    this.store.setName((event.target as HTMLInputElement).value);
  }

  protected onDimension(key: keyof TerrainDimensions, event: Event): void {
    this.store.setDimension(key, Number.parseFloat((event.target as HTMLInputElement).value));
  }

  protected onSoil(event: Event): void {
    this.store.setSoil((event.target as HTMLSelectElement).value as SoilType);
  }

  protected onSlope(event: Event): void {
    this.store.setSlope(Number.parseFloat((event.target as HTMLInputElement).value));
  }

  protected guardar(): void {
    this.store.guardar();
  }

  /** El usuario dice que conoce la pendiente: se revela el control. */
  protected definirPendiente(): void {
    this.store.setSlope(this.store.slopePct());
  }

  protected usarPendienteAsumida(): void {
    this.store.usarPendienteAsumida();
  }
}
