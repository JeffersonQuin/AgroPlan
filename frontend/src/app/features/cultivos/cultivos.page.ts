import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { WizardDraftStore } from '../wizard/state/wizard-draft.store';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
import { CultivoForm } from './components/cultivo-form/cultivo-form';
import { CultivosCroquis } from './components/cultivos-croquis/cultivos-croquis';
import { CultivosPanel } from './components/cultivos-panel/cultivos-panel';
import { CultivosStore } from './state/cultivos.store';

/**
 * Step 2: which products to sow.
 *
 * It only collects — products and the sowing date — and reads the terrain from step 1.
 * Nothing is written and the agent is not called: the distribution, the harvest dates
 * and the irrigation system arrive in one single run at the final summary.
 */
@Component({
  selector: 'app-cultivos-page',
  imports: [RouterLink, WizardHeader, CultivoForm, CultivosCroquis, CultivosPanel],
  templateUrl: './cultivos.page.html',
})
export class CultivosPage {
  protected readonly store = inject(CultivosStore);
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
