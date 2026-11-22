import { Component, inject } from '@angular/core';
import { WizardDraftStore } from '../../../wizard/state/wizard-draft.store';
import { CultivosStore } from '../../state/cultivos.store';

/**
 * Right rail of step 2: what the step collected and what the final summary will show.
 *
 * The product list lives in the centre column; here only the counts, the terrain data
 * read in step 1 and the promise of what step 4 delivers.
 */
@Component({
  selector: 'app-cultivos-panel',
  templateUrl: './cultivos-panel.html',
})
export class CultivosPanel {
  protected readonly store = inject(CultivosStore);
  protected readonly borrador = inject(WizardDraftStore);
}
