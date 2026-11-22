import { Component, inject } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matBoltOutline,
  matSolarPowerOutline,
  matWaterDropOutline,
} from '@ng-icons/material-symbols/outline';
import {
  ENERGIA_OPTIONS,
  EnergiaDisponible,
  EnergiaIcono,
  PRESUPUESTO_MINIMO_BS,
  TANQUE_DEPOSITO_OPTIONS,
  TANQUE_OPTIONS,
} from '../../../wizard/models/restricciones.model';
import { WizardDraftStore } from '../../../wizard/state/wizard-draft.store';
import { RiegoStore } from '../../state/riego.store';

/**
 * The registry name of the icon each `EnergiaIcono` key renders.
 *
 * `provideIcons({ matBoltOutline })` registers that name as the key and the SVG as the value,
 * so the name `[name]` receives must be the string, never the SVG constant.
 */
const ENERGIA_ICONS: Record<EnergiaIcono, string> = {
  bolt: 'matBoltOutline',
  solar_power: 'matSolarPowerOutline',
};

/**
 * Left rail of step 3: the restrictions the user already has.
 *
 * Only three inputs — energy, tank, budget — because the irrigation system, the trace,
 * the sectors and the materials are the agent's job in step 4.
 */
@Component({
  selector: 'app-riego-form',
  imports: [NgIcon],
  viewProviders: [provideIcons({ matBoltOutline, matSolarPowerOutline, matWaterDropOutline })],
  templateUrl: './riego-form.html',
})
export class RiegoForm {
  protected readonly borrador = inject(WizardDraftStore);
  protected readonly store = inject(RiegoStore);

  protected readonly energias = ENERGIA_OPTIONS;
  protected readonly tanques = TANQUE_OPTIONS;
  protected readonly tanquesDeposito = TANQUE_DEPOSITO_OPTIONS;
  protected readonly presupuestoMinimo = PRESUPUESTO_MINIMO_BS;

  protected elegirEnergia(energia: EnergiaDisponible): void {
    this.borrador.setEnergia(energia);
  }

  /** Resolves a dynamic icon key to the constant declared in `provideIcons`. */
  protected iconoEnergia(icono: EnergiaIcono): string {
    return ENERGIA_ICONS[icono];
  }

  protected elegirTanque(valor: string): void {
    this.borrador.setTanqueL(valor === '' ? null : Number(valor));
  }

  protected onPresupuesto(valor: string): void {
    this.borrador.setPresupuestoBs(valor);
  }
}
