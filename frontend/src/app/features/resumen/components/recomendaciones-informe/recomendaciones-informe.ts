import { Component, input } from '@angular/core';
import { RecomendacionInformeApi } from '../../models/resumen.model';

/** Recomendaciones finales del agente con su justificación (S7). */
@Component({
  selector: 'app-recomendaciones-informe',
  templateUrl: './recomendaciones-informe.html',
})
export class RecomendacionesInforme {
  readonly recomendaciones = input<RecomendacionInformeApi[]>([]);
}
