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

  protected readonly formatearFecha = formatearFecha;

  protected titulo(fuente: FuenteInformeApi): string {
    return fuente.titulo ?? fuente.url ?? 'no informado';
  }
}
