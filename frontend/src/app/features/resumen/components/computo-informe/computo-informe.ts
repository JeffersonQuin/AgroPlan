import { Component, input } from '@angular/core';
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

  protected readonly formatearFecha = formatearFecha;
  protected readonly formatearNumero = formatearNumero;

  protected estadoPresupuesto(): string {
    if (this.presupuestoExcedido() === true) return 'Presupuesto excedido';
    if (this.presupuestoExcedido() === false) return 'Dentro del presupuesto';
    return 'Presupuesto no informado';
  }

  protected claseEstado(): string {
    if (this.presupuestoExcedido() === true) {
      return 'bg-red-50 text-red-700 border-red-200';
    }
    if (this.presupuestoExcedido() === false) {
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    return 'bg-slate-100 text-slate-500 border-slate-200';
  }
}
