import { Component, computed, input } from '@angular/core';
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
  /** Corrida resuelta con el catálogo interno: una línea, no cinco "no informado" (S3). */
  readonly modoCatalogo = input(false);

  protected readonly etiquetaCampoAjuste = etiquetaCampoAjuste;
  protected readonly formatearConUnidad = formatearConUnidad;
  protected readonly formatearNumero = formatearNumero;

  /** El agente no propuso ninguna cifra: en modo catálogo se explica en una línea. */
  protected readonly sinCifrasAgente = computed(() => {
    const cifras = this.cifrasAgente();
    if (cifras === null) return true;
    return (
      cifras.presion_trabajo_bar === null &&
      cifras.eficiencia_pct === null &&
      cifras.demanda_pico_l_dia === null &&
      cifras.autonomia_dias === null &&
      cifras.tiempo_riego_h === null &&
      cifras.turnos.length === 0
    );
  });

  protected valorAgente(valor: string | null): string {
    return valor ?? 'no informado';
  }

  protected valorMotor(valor: string | null): string {
    return valor ?? 'no informado';
  }
}
