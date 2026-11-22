import { Component, inject } from '@angular/core';
import { WizardDraftStore } from '../../../wizard/state/wizard-draft.store';
import { CultivosStore } from '../../state/cultivos.store';

/**
 * Right rail of step 2: the products already configured.
 *
 * Only what the user chose is shown here. The area, the demand, the harvest dates and
 * the soil verdict arrive in the final summary: this step does not ask the agent.
 */
@Component({
  selector: 'app-cultivos-panel',
  templateUrl: './cultivos-panel.html',
})
export class CultivosPanel {
  protected readonly store = inject(CultivosStore);
  protected readonly borrador = inject(WizardDraftStore);

  protected colorDe(codigo: string | null, color: string): string {
    if (codigo === null) return color;
    return this.store.opcionesCultivo().find((opcion) => opcion.value === codigo)?.color ?? color;
  }
}
