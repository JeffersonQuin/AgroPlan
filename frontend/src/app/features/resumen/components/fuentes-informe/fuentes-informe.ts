import { Component, input } from '@angular/core';
import { formatearFecha } from '../../formato-informe';
import { FuenteInformeApi } from '../../models/resumen.model';

/** Fuentes web que consultó el agente (S7). */
@Component({
  selector: 'app-fuentes-informe',
  templateUrl: './fuentes-informe.html',
})
export class FuentesInforme {
  readonly fuentes = input<FuenteInformeApi[]>([]);
  /** Sin credenciales no hubo investigación web: se dice explícitamente (S5). */
  readonly modoCatalogo = input(false);

  protected readonly formatearFecha = formatearFecha;

  protected titulo(fuente: FuenteInformeApi): string {
    return fuente.titulo ?? fuente.url ?? 'no informado';
  }
}
