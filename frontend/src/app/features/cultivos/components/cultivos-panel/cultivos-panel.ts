import { Component, computed, inject, output } from '@angular/core';
import { BloqueApi } from '../../models/cultivos.model';
import { CultivosStore } from '../../state/cultivos.store';

/** Right rail of step 2: the configured crops and the balance panel. */
@Component({
  selector: 'app-cultivos-panel',
  templateUrl: './cultivos-panel.html',
})
export class CultivosPanel {
  protected readonly store = inject(CultivosStore);

  readonly editar = output<BloqueApi>();

  protected readonly anchoBarra = computed(() => Math.min(this.store.asignadoPct(), 100));

  protected colorDe(codigo: string): string {
    return this.store.opcionesCultivo().find((opcion) => opcion.value === codigo)?.color ?? '#4CAF50';
  }

  protected nombreDe(codigo: string): string {
    return this.store.opcionesCultivo().find((opcion) => opcion.value === codigo)?.label ?? codigo;
  }

  protected veredictoClase(bloque: BloqueApi): string {
    switch (bloque.aptitud_suelo?.veredicto) {
      case 'apto':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'condicionado':
        return 'text-amber-700 bg-amber-50 border-amber-200';
      case 'no_apto':
        return 'text-error bg-error-container/40 border-error/30';
      default:
        return 'hidden';
    }
  }

  protected eliminar(bloque: BloqueApi): void {
    this.store.eliminar(bloque.id)?.subscribe();
  }
}
