import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
import { WizardDraftStore } from '../wizard/state/wizard-draft.store';
import { RiegoForm } from './components/riego-form/riego-form';
import { RiegoStore } from './state/riego.store';

/**
 * Step 3: the irrigation restrictions the user already has.
 *
 * It only collects — energy, existing tank and an optional budget — and reads the water
 * source the terrain declared in step 1. The system, the trace, the sectors, the turns
 * and the material take-off are produced by the agent in step 4.
 */
@Component({
  selector: 'app-riego-page',
  imports: [RouterLink, WizardHeader, RiegoForm],
  templateUrl: './riego.page.html',
})
export class RiegoPage {
  protected readonly store = inject(RiegoStore);
  protected readonly borrador = inject(WizardDraftStore);
  private readonly route = inject(ActivatedRoute);

  protected readonly proyectoId = signal('');

  constructor() {
    const proyectoId = this.route.snapshot.paramMap.get('proyectoId') ?? '';
    this.proyectoId.set(proyectoId);
    if (proyectoId !== '') {
      this.store.cargar(proyectoId);
      this.borrador.cargar(proyectoId);
    }
  }
}
