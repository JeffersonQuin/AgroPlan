import { Component, computed, input, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { matCheckOutline } from '@ng-icons/material-symbols/outline';

interface PasoWizard {
  numero: number;
  nombre: string;
}

const PASOS: readonly PasoWizard[] = [
  { numero: 1, nombre: 'Terreno' },
  { numero: 2, nombre: 'Cultivos' },
  { numero: 3, nombre: 'Sistema' },
  { numero: 4, nombre: 'Resultado' },
];

/**
 * Wizard chrome shared by the four steps: brand, project name, the stepper and the
 * save state. Each page hands it the current step and its own state, so the header
 * never reaches into another feature's store.
 */
@Component({
  selector: 'app-wizard-header',
  imports: [NgIcon],
  viewProviders: [provideIcons({ matCheckOutline })],
  templateUrl: './wizard-header.html',
})
export class WizardHeader {
  readonly paso = input<number>(1);
  readonly nombreProyecto = input<string>('Proyecto');
  readonly estadoGuardado = input<string>('Sin guardar');
  readonly guardar = output<void>();

  protected readonly pasos = PASOS;
  protected readonly actual = computed(() => this.paso());

  protected estadoPaso(numero: number): 'hecho' | 'activo' | 'pendiente' {
    if (numero < this.actual()) return 'hecho';
    return numero === this.actual() ? 'activo' : 'pendiente';
  }
}
