import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { matAddOutline, matPottedPlantOutline } from '@ng-icons/material-symbols/outline';
import { WizardDraftStore } from '../../../wizard/state/wizard-draft.store';
import { CultivosStore } from '../../state/cultivos.store';

/**
 * Left rail of step 2: the product list and the sowing date.
 *
 * Step 2 only collects: no write and no agent call. The distribution, the harvest
 * dates and every figure arrive in the final summary (step 4), from one single run.
 */
@Component({
  selector: 'app-cultivo-form',
  imports: [FormsModule, NgIcon],
  viewProviders: [provideIcons({ matAddOutline, matPottedPlantOutline })],
  templateUrl: './cultivo-form.html',
})
export class CultivoForm {
  protected readonly store = inject(CultivosStore);
  protected readonly borrador = inject(WizardDraftStore);

  protected readonly codigo = signal<string | null>(null);
  protected readonly nuevo = signal('');
  protected readonly aviso = signal<string | null>(null);

  /** Sólo los cultivos que todavía no están en la lista. */
  protected readonly opciones = computed(() =>
    this.store
      .opcionesCultivo()
      .filter(
        (opcion) => !this.borrador.productos().some((producto) => producto.codigo === opcion.value),
      ),
  );

  protected readonly puedeAgregarCatalogo = computed(() => this.opciones().length > 0);

  protected readonly motivoSinCatalogo = computed(() =>
    this.opciones().length === 0 ? 'Ya agregaste todos los cultivos del catálogo' : null,
  );

  protected agregarDelCatalogo(): void {
    const elegido = this.codigo() ?? this.opciones()[0]?.value ?? null;
    const opcion = this.opciones().find((candidato) => candidato.value === elegido);
    if (opcion === undefined) return;
    this.borrador.agregarProducto(opcion.value, '', opcion.label, opcion.color);
    this.codigo.set(null);
  }

  protected agregarNuevo(): void {
    const texto = this.nuevo().trim();
    if (texto.length < 2) {
      this.aviso.set('Escribí al menos 2 letras del producto (por ejemplo: yuca).');
      return;
    }
    this.aviso.set(null);
    this.borrador.agregarProducto(null, texto, texto, '#4CAF50');
    this.nuevo.set('');
  }

  protected onNuevo(valor: string): void {
    this.nuevo.set(valor);
    if (this.aviso() !== null) this.aviso.set(null);
  }
}
