import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { TerrainCanvas } from './components/terrain-canvas/terrain-canvas';
import { TerrainForm } from './components/terrain-form/terrain-form';
import { TerrainSummary } from './components/terrain-summary/terrain-summary';
import { WizardHeader } from './components/wizard-header/wizard-header';
import { TerrainStore } from './state/terrain.store';

/**
 * Step 1 of the project wizard: terrain definition.
 *
 * The route carries the project id; the store loads the project name, the saved
 * terrain (when re-entering) and the soil catalogue, and the backend becomes the
 * source of truth for area, perimeter and effective flow rate.
 */
@Component({
  selector: 'app-terrain-page',
  imports: [WizardHeader, TerrainForm, TerrainCanvas, TerrainSummary],
  templateUrl: './terrain.page.html',
})
export class TerrainPage {
  protected readonly store = inject(TerrainStore);
  private readonly route = inject(ActivatedRoute);

  constructor() {
    const proyectoId = this.route.snapshot.paramMap.get('proyectoId');
    if (proyectoId !== null) this.store.cargar(proyectoId);
  }
}
