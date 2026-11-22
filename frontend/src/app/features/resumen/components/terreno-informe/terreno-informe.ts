import { Component, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matArrowForwardOutline,
  matLandscapeOutline,
  matLocationOnOutline,
  matWaterDropOutline,
} from '@ng-icons/material-symbols/outline';
import { aHectareas, formatearNumero } from '../../formato-informe';
import { ResumenStore } from '../../state/resumen.store';

/** Datos del terreno del paso 1, con su link para corregirlos (S1). */
@Component({
  selector: 'app-terreno-informe',
  imports: [RouterLink, NgIcon],
  viewProviders: [
    provideIcons({ matArrowForwardOutline, matLandscapeOutline, matLocationOnOutline, matWaterDropOutline }),
  ],
  templateUrl: './terreno-informe.html',
})
export class TerrenoInforme {
  protected readonly store = inject(ResumenStore);
  readonly proyectoId = input<string>('');

  protected readonly aHectareas = aHectareas;
  protected readonly formatearNumero = formatearNumero;
}
