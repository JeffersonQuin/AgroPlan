import { Component, inject } from '@angular/core';
import { WATER_SOURCE_OPTIONS, WaterSource } from '../../models/terrain.model';
import { TerrainStore } from '../../state/terrain.store';

/** Right rail of the terrain step: geometry summary, validations and water. */
@Component({
  selector: 'app-terrain-summary',
  templateUrl: './terrain-summary.html',
})
export class TerrainSummary {
  protected readonly store = inject(TerrainStore);

  protected readonly waterOptions = WATER_SOURCE_OPTIONS;

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

  protected onFlow(event: Event): void {
    this.store.setFlow(Number.parseFloat((event.target as HTMLInputElement).value));
  }

  protected onLevel(event: Event): void {
    this.store.setStaticLevel(Number.parseFloat((event.target as HTMLInputElement).value));
  }
}
