import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TerrainCanvas } from './components/terrain-canvas/terrain-canvas';
import { TerrainForm } from './components/terrain-form/terrain-form';
import { TerrainSummary } from './components/terrain-summary/terrain-summary';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
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
  private readonly router = inject(Router);
  protected readonly proyectoId = signal('');

  constructor() {
    const proyectoId = this.route.snapshot.paramMap.get('proyectoId') ?? '';
    this.proyectoId.set(proyectoId);
    if (proyectoId !== '') this.store.cargar(proyectoId);
  }

  /** Guardar y continuar: se guarda el terreno y recién ahí se avanza al paso 2. */
  protected onContinuar(): void {
    this.store.guardar()?.subscribe({
      next: () => void this.router.navigate(['/proyectos', this.proyectoId(), 'cultivos']),
    });
  }
}
