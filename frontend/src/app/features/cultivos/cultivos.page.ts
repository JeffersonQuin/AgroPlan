import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
import { CultivoForm } from './components/cultivo-form/cultivo-form';
import { CultivosCroquis } from './components/cultivos-croquis/cultivos-croquis';
import { CultivosPanel } from './components/cultivos-panel/cultivos-panel';
import { BloqueApi } from './models/cultivos.model';
import { CultivosStore } from './state/cultivos.store';

/**
 * Step 2: the user adds products and the agent distributes the terrain.
 *
 * The distribution is painted only after the agent answers: while the list is being
 * built (and if it fails) the canvas shows the terrain as it was drawn in step 1.
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
  protected readonly confirmarGeneracion = signal(false);
  protected readonly modalPremium = signal(false);

  protected readonly tituloGenerar = computed(() =>
    this.store.generado() ? 'Regenerar distribución' : 'Generar distribución',
  );

  constructor() {
    const proyectoId = this.route.snapshot.paramMap.get('proyectoId') ?? '';
    this.proyectoId.set(proyectoId);
    if (proyectoId !== '') this.store.cargar(proyectoId);
  }

  /** El primer generar avisa que consume el agente y no se repite gratis. */
  protected pedirGeneracion(): void {
    if (this.store.generado()) {
      this.modalPremium.set(true);
      return;
    }
    this.confirmarGeneracion.set(true);
  }

  protected confirmar(): void {
    this.confirmarGeneracion.set(false);
    this.store.generar();
  }

  protected cerrarConfirmacion(): void {
    this.confirmarGeneracion.set(false);
  }

  protected cerrarPremium(): void {
    this.modalPremium.set(false);
  }

  protected onEditar(bloque: BloqueApi): void {
    this.store.seleccionar(bloque.cultivo_codigo);
    this.modalPremium.set(true);
  }
}
