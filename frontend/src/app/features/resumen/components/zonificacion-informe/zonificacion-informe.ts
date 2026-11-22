import { Component, input } from '@angular/core';
import { formatearFecha, formatearNumero } from '../../formato-informe';
import { BloqueInformeApi } from '../../models/resumen.model';

/** Zonificación agronómica: una tarjeta por bloque, con imagen y crédito (S1, S4). */
@Component({
  selector: 'app-zonificacion-informe',
  templateUrl: './zonificacion-informe.html',
})
export class ZonificacionInforme {
  readonly bloques = input<BloqueInformeApi[]>([]);

  protected readonly formatearFecha = formatearFecha;
  protected readonly formatearNumero = formatearNumero;

  protected nombre(bloque: BloqueInformeApi): string {
    return bloque.nombre ?? bloque.cultivo_codigo;
  }

  protected inicial(bloque: BloqueInformeApi): string {
    return this.nombre(bloque).charAt(0).toUpperCase();
  }
}
