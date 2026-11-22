import { Component, OnDestroy, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matArrowBackOutline,
  matArrowForwardOutline,
  matBoltOutline,
  matCheckCircleOutline,
  matErrorOutline,
  matEventOutline,
  matInfoOutline,
  matLocationOnOutline,
  matPaymentsOutline,
  matProgressActivityOutline,
  matSummarizeOutline,
  matWaterDropOutline,
  matWaterOutline,
} from '@ng-icons/material-symbols/outline';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
import { WizardDraftStore } from '../wizard/state/wizard-draft.store';
import { ResumenStore } from './state/resumen.store';

/**
 * Step 4: the final report.
 *
 * The screen owns the flow — no draft, review modal, running agent, error, report —
 * and stops polling when it is destroyed. The report sections themselves consume
 * `store.resultado()`.
 */
@Component({
  selector: 'app-resumen-page',
  imports: [RouterLink, WizardHeader, NgIcon],
  viewProviders: [
    provideIcons({
      matArrowBackOutline,
      matArrowForwardOutline,
      matBoltOutline,
      matCheckCircleOutline,
      matErrorOutline,
      matEventOutline,
      matInfoOutline,
      matLocationOnOutline,
      matPaymentsOutline,
      matProgressActivityOutline,
      matSummarizeOutline,
      matWaterDropOutline,
      matWaterOutline,
    }),
  ],
  templateUrl: './resumen.page.html',
})
export class ResumenPage implements OnDestroy {
  protected readonly store = inject(ResumenStore);
  protected readonly borrador = inject(WizardDraftStore);
  private readonly route = inject(ActivatedRoute);

  protected readonly proyectoId = signal('');

  constructor() {
    const proyectoId = this.route.snapshot.paramMap.get('proyectoId') ?? '';
    this.proyectoId.set(proyectoId);
    if (proyectoId !== '') {
      // El borrador primero: el store decide `sin-borrador` leyéndolo.
      this.borrador.cargar(proyectoId);
      this.store.cargar(proyectoId);
    }
  }

  ngOnDestroy(): void {
    this.store.detenerSondeo();
  }
}
