import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
import { CultivoForm } from './components/cultivo-form/cultivo-form';
import { CultivosCroquis } from './components/cultivos-croquis/cultivos-croquis';
import { CultivosPanel } from './components/cultivos-panel/cultivos-panel';
import { BloqueApi } from './models/cultivos.model';
import { CultivosStore } from './state/cultivos.store';

/**
 * Step 2: crop distribution.
 *
 * The route carries the project id; the store loads the project, its terrain, the
 * blocks, the balance panel and the crop catalogue, and every write refreshes the
 * backend-calculated figures.
 */
@Component({
  selector: 'app-cultivos-page',
  imports: [RouterLink, WizardHeader, CultivoForm, CultivosCroquis, CultivosPanel],
  templateUrl: './cultivos.page.html',
})
export class CultivosPage {
  protected readonly store = inject(CultivosStore);
  private readonly route = inject(ActivatedRoute);

  protected readonly proyectoId = signal('');

  constructor() {
    const proyectoId = this.route.snapshot.paramMap.get('proyectoId') ?? '';
    this.proyectoId.set(proyectoId);
    if (proyectoId !== '') this.store.cargar(proyectoId);
  }

  /** La fila del panel pide editar: el formulario se llena con ese bloque. */
  protected onEditar(bloque: BloqueApi): void {
    this.store.seleccionar(bloque.cultivo_codigo);
    void bloque;
  }
}
