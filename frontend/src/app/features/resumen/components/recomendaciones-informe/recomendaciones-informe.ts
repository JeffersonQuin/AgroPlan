import { Component, input } from '@angular/core';
import { RecomendacionInformeApi } from '../../models/resumen.model';

/** Clave para comparar textos: sin espacios de más, mayúsculas ni punto final. */
function comparable(texto: string | null): string {
  return (texto ?? '').replace(/\s+/g, ' ').trim().toLowerCase().replace(/\.$/, '');
}

/** Recomendaciones finales del agente con su justificación (S7). */
@Component({
  selector: 'app-recomendaciones-informe',
  templateUrl: './recomendaciones-informe.html',
})
export class RecomendacionesInforme {
  readonly recomendaciones = input<RecomendacionInformeApi[]>([]);

  /** S5: el detalle no repite el título. */
  protected mostrarDetalle(recomendacion: RecomendacionInformeApi): boolean {
    const detalle = comparable(recomendacion.detalle);
    return detalle !== '' && detalle !== comparable(recomendacion.titulo);
  }

  /** S5: la justificación no repite el título ni el detalle. */
  protected mostrarJustificacion(recomendacion: RecomendacionInformeApi): boolean {
    const justificacion = comparable(recomendacion.justificacion);
    return (
      justificacion !== '' &&
      justificacion !== comparable(recomendacion.titulo) &&
      justificacion !== comparable(recomendacion.detalle)
    );
  }
}
