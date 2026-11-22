import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BloqueApi } from '../../models/cultivos.model';
import { CultivosStore } from '../../state/cultivos.store';

/**
 * Left rail of step 2: the agronomic parameters of the crop being configured.
 *
 * The figures (consumption, cycle, Kc) come from the catalogue; the user only picks
 * the species, how much of the parcel it takes and, optionally, the dates.
 */
@Component({
  selector: 'app-cultivo-form',
  imports: [FormsModule],
  templateUrl: './cultivo-form.html',
})
export class CultivoForm {
  protected readonly store = inject(CultivosStore);

  protected readonly codigo = signal('');
  protected readonly porcentaje = signal<number | null>(null);
  protected readonly etiqueta = signal('');
  protected readonly siembra = signal('');
  protected readonly cosecha = signal('');
  protected readonly editando = signal<BloqueApi | null>(null);

  protected readonly disponibles = computed(() =>
    Math.max(0, Math.round((100 - this.store.asignadoPct()) * 10) / 10),
  );

  protected readonly opciones = computed(() =>
    this.store.opcionesCultivo().filter(
      (opcion) => !this.editando() && !this.store.bloques().some((b) => b.cultivo_codigo === opcion.value),
    ),
  );

  /** Lo que muestra el bloque de parámetros técnicos. */
  protected readonly ficha = computed(() => {
    if (this.editando() !== null) return null;
    const codigo = this.codigo() || this.opciones()[0]?.value;
    return this.store.opcionesCultivo().find((opcion) => opcion.value === codigo) ?? null;
  });

  protected readonly puedeAgregar = computed(() => {
    const porcentaje = this.porcentaje();
    return this.ficha() !== null && porcentaje !== null && porcentaje > 0 && porcentaje <= this.disponibles();
  });

  protected usarDisponible(): void {
    this.porcentaje.set(this.disponibles());
  }

  protected agregar(): void {
    const ficha = this.ficha();
    const porcentaje = this.porcentaje();
    if (ficha === null || porcentaje === null) return;

    const bloque = this.editando();
    if (bloque !== null) {
      this.store
        .editar(bloque.id, {
          porcentaje,
          etiqueta: this.etiqueta().trim() || bloque.etiqueta,
          siembra: this.siembra() || null,
          cosecha: this.cosecha() || null,
        })
        ?.subscribe({ next: () => this.limpiar() });
      return;
    }

    this.store
      .agregar(ficha.value, porcentaje, this.etiqueta().trim() || null)
      ?.subscribe({ next: () => this.limpiar() });
  }

  protected editar(bloque: BloqueApi): void {
    this.editando.set(bloque);
    this.codigo.set(bloque.cultivo_codigo);
    this.porcentaje.set(bloque.porcentaje);
    this.etiqueta.set(bloque.etiqueta ?? '');
    this.siembra.set(bloque.siembra ?? '');
    this.cosecha.set(bloque.cosecha ?? '');
  }

  protected limpiar(): void {
    this.editando.set(null);
    this.codigo.set('');
    this.porcentaje.set(null);
    this.etiqueta.set('');
    this.siembra.set('');
    this.cosecha.set('');
  }

  protected onNumero(valor: string): void {
    const numero = Number.parseFloat(valor);
    this.porcentaje.set(Number.isFinite(numero) ? numero : null);
  }
}
