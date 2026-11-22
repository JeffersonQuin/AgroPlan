import { Component, input } from '@angular/core';
import { formatearFecha } from '../../formato-informe';
import { CalendarioBloqueApi } from '../../models/resumen.model';

/** Calendario agronómico: siembra y cosecha por bloque (S9). */
@Component({
  selector: 'app-calendario-informe',
  templateUrl: './calendario-informe.html',
})
export class CalendarioInforme {
  readonly calendario = input<CalendarioBloqueApi[]>([]);

  protected readonly formatearFecha = formatearFecha;

  protected nombre(bloque: CalendarioBloqueApi): string {
    return bloque.etiqueta ?? bloque.cultivo_codigo;
  }
}
