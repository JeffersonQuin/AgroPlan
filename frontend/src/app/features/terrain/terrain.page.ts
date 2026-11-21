import { Component } from '@angular/core';
import { TerrainCanvas } from './components/terrain-canvas/terrain-canvas';
import { TerrainForm } from './components/terrain-form/terrain-form';
import { TerrainSummary } from './components/terrain-summary/terrain-summary';
import { WizardHeader } from './components/wizard-header/wizard-header';

/**
 * Step 1 of the project wizard: terrain definition.
 *
 * The canvas is the reference drawing of the mockup and stays static; the cotas,
 * the slope, the soil and the water source drive both side rails.
 */
@Component({
  selector: 'app-terrain-page',
  imports: [WizardHeader, TerrainForm, TerrainCanvas, TerrainSummary],
  templateUrl: './terrain.page.html',
})
export class TerrainPage {}
