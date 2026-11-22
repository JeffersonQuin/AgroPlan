import { Component, inject } from '@angular/core';
import {
  ENERGIA_OPTIONS,
  EnergiaDisponible,
  PRESUPUESTO_MINIMO_BS,
  TANQUE_DEPOSITO_OPTIONS,
  TANQUE_OPTIONS,
} from '../../../wizard/models/restricciones.model';
import { WizardDraftStore } from '../../../wizard/state/wizard-draft.store';
import { RiegoStore } from '../../state/riego.store';

/**
 * Left rail of step 3: the restrictions the user already has.
 *
 * Only three inputs — energy, tank, budget — because the irrigation system, the trace,
 * the sectors and the materials are the agent's job in step 4.
 */
@Component({
  selector: 'app-riego-form',
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

  protected elegirTanque(valor: string): void {
    this.borrador.setTanqueL(valor === '' ? null : Number(valor));
  }

  protected onPresupuesto(valor: string): void {
    this.borrador.setPresupuestoBs(valor);
  }
}
