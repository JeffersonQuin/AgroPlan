import { Component, input } from '@angular/core';
import { etiquetaCampoAjuste, formatearConUnidad, formatearNumero } from '../../formato-informe';
import { AjusteMotorApi, CifrasAgenteApi, CifrasMotorApi } from '../../models/resumen.model';

/** Balance hidráulico: cifras del motor, las del agente y cada ajuste explicado (S3, S9). */
@Component({
  selector: 'app-balance-informe',
  templateUrl: './balance-informe.html',
})
export class BalanceInforme {
  readonly cifras = input.required<CifrasMotorApi>();
  readonly cifrasAgente = input<CifrasAgenteApi | null>(null);
  readonly eficiencia = input<number | null>(null);
  readonly ajustes = input<AjusteMotorApi[]>([]);

  protected readonly etiquetaCampoAjuste = etiquetaCampoAjuste;
  protected readonly formatearConUnidad = formatearConUnidad;
  protected readonly formatearNumero = formatearNumero;

  protected valorAgente(valor: string | null): string {
    return valor ?? 'no informado';
  }

  protected valorMotor(valor: string | null): string {
    return valor ?? 'no informado';
  }
}
