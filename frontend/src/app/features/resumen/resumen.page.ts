import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
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
} from '@ng-icons/material-symbols/outline';
import { WizardHeader } from '../wizard/components/wizard-header/wizard-header';
import { WizardDraftStore } from '../wizard/state/wizard-draft.store';
import { AdvertenciasInforme } from './components/advertencias-informe/advertencias-informe';
import { BalanceInforme } from './components/balance-informe/balance-informe';
import { CalendarioInforme } from './components/calendario-informe/calendario-informe';
import { ComputoInforme } from './components/computo-informe/computo-informe';
import { FuentesInforme } from './components/fuentes-informe/fuentes-informe';
import { PlanoRed } from './components/plano-red/plano-red';
import { RecomendacionesInforme } from './components/recomendaciones-informe/recomendaciones-informe';
import { TecnologiaInforme } from './components/tecnologia-informe/tecnologia-informe';
import { TerrenoInforme } from './components/terreno-informe/terreno-informe';
import { ZonificacionInforme } from './components/zonificacion-informe/zonificacion-informe';
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
  imports: [
    RouterLink,
    WizardHeader,
    NgIcon,
    AdvertenciasInforme,
    BalanceInforme,
    CalendarioInforme,
    ComputoInforme,
    FuentesInforme,
    PlanoRed,
    RecomendacionesInforme,
    TecnologiaInforme,
    TerrenoInforme,
    ZonificacionInforme,
  ],
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
    }),
  ],
  templateUrl: './resumen.page.html',
})
export class ResumenPage implements OnDestroy {
  protected readonly store = inject(ResumenStore);
  protected readonly borrador = inject(WizardDraftStore);
  private readonly route = inject(ActivatedRoute);

  protected readonly proyectoId = signal('');

  /**
   * Advertencias visibles arriba de todo el informe: las del resultado y las que
   * dejó el diseño generado (por ejemplo, un ajuste del motor).
   *
   * El backend repite las del diseño en el resultado, así que se deduplican por
   * código y mensaje: el usuario no tiene que leer dos veces el mismo aviso.
   */
  protected readonly advertenciasInforme = computed(() => {
    const vistas = new Set<string>();
    return [
      ...this.store.advertencias(),
      ...(this.store.resultado()?.diseno.advertencias ?? []),
    ].filter((advertencia) => {
      const clave = `${advertencia.codigo}|${advertencia.mensaje}`;
      if (vistas.has(clave)) return false;
      vistas.add(clave);
      return true;
    });
  });

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
