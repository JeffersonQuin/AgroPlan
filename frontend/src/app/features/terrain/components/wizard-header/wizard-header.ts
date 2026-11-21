import { Component, inject } from '@angular/core';
import { TerrainStore } from '../../state/terrain.store';

/** Wizard chrome: project name, the four steps and the save state. */
@Component({
  selector: 'app-wizard-header',
  templateUrl: './wizard-header.html',
})
export class WizardHeader {
  protected readonly store = inject(TerrainStore);
}
