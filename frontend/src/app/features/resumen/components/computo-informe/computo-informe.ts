import { Component, computed, input } from '@angular/core';
import { formatearFecha, formatearNumero } from '../../formato-informe';
import { MaterialInformeApi } from '../../models/resumen.model';

/** Cómputo de materiales con precios, reutilización y presupuesto (S6). */
@Component({
  selector: 'app-computo-informe',
  templateUrl: './computo-informe.html',
})
export class ComputoInforme {
  readonly materiales = input<MaterialInformeApi[]>([]);
  readonly costoTotalBs = input<number | null>(null);
  readonly presupuestoBs = input<number | null>(null);
  readonly presupuestoExcedido = input<boolean | null>(null);
  /** Corrida resuelta con el catálogo interno: sin precios no hay cómputo (S3). */
  readonly modoCatalogo = input(false);

  protected readonly formatearFecha = formatearFecha;
  protected readonly formatearNumero = formatearNumero;

  /**
   * El chip sólo existe cuando hay una comparación real. Sin costos no se puede
   * decir "presupuesto no informado": la cifra al lado ya lo desmiente (S3).
   */
  protected readonly mostrarEstado = computed(() => this.presupuestoExcedido() !== null);

  /** Presupuesto informado pero sin cómputo: falta el costo, no el presupuesto. */
  protected readonly sinCostos = computed(
    () => this.costoTotalBs() === null && this.presupuestoBs() !== null,
  );

  protected estadoPresupuesto(): string {
    return this.presupuestoExcedido() === true ? 'Presupuesto excedido' : 'Dentro del presupuesto';
  }

  protected claseEstado(): string {
    return this.presupuestoExcedido() === true
      ? 'bg-red-50 text-red-700 border-red-200'
      : 'bg-emerald-50 text-emerald-700 border-emerald-200';
  }
}
