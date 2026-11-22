import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CultivosStore } from '../../state/cultivos.store';

/**
 * Left rail of step 2: the product list.
 *
 * The user only picks products — from the catalogue or typed by hand — and the sowing
 * date. The distribution is the agent's job: there are no percentages to fill here.
 */
@Component({
  selector: 'app-cultivo-form',
  imports: [FormsModule],
  templateUrl: './cultivo-form.html',
})
export class CultivoForm {
  protected readonly store = inject(CultivosStore);

  protected readonly codigo = signal<string | null>(null);
  protected readonly nuevo = signal('');
  /** Motivo visible cuando el botón de agregar no hace nada. */
  protected readonly aviso = signal<string | null>(null);

  protected readonly opciones = computed(() =>
    this.store
      .opcionesCultivo()
      .filter(
        (opcion) => !this.store.productos().some((producto) => producto.codigo === opcion.value),
      ),
  );

  protected readonly puedeAgregarCatalogo = computed(
    () => this.codigo() !== null || this.opciones().length > 0,
  );

  protected agregarDelCatalogo(): void {
    const codigo = this.codigo() ?? this.opciones()[0]?.value ?? null;
    if (codigo === null) return;
    this.store.agregarProducto(codigo, '');
    this.codigo.set(null);
  }

  protected agregarNuevo(): void {
    const texto = this.nuevo().trim();
    if (texto.length < 2) {
      this.aviso.set('Escribí al menos 2 letras del producto (por ejemplo: yuca).');
      return;
    }
    this.aviso.set(null);
    this.store.agregarProducto(null, texto);
    this.nuevo.set('');
  }

  protected onNuevo(valor: string): void {
    this.nuevo.set(valor);
    if (this.aviso() !== null) this.aviso.set(null);
  }

  /** Por qué el botón del catálogo no puede agregar nada. */
  protected readonly motivoSinCatalogo = computed(() => {
    if (this.store.generado()) return 'La distribución ya está generada';
    if (this.opciones().length === 0) return 'Ya agregaste todos los cultivos del catálogo';
    return null;
  });
}
