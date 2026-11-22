import { Component, InjectionToken, OnDestroy, computed, inject, input, signal } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matCheckCircleOutline,
  matProgressActivityOutline,
  matRadioButtonUncheckedOutline,
} from '@ng-icons/material-symbols/outline';
import {
  ESPERA_LARGA_MODELO_SEGUNDOS,
  FASE_MODELO,
  FASES_CORRIDA,
  MODELO_TARDA_SEGUNDOS,
  indiceDeFase,
} from '../../fases-corrida';

/** Cómo se ve cada fase del stepper. */
type EstadoFase = 'cumplida' | 'actual' | 'pendiente';

/**
 * Reloj del cronómetro.
 *
 * Inyectable para que los tests fijen el instante sin depender del reloj real: el
 * valor sale siempre de `Date.now()` en producción (S4).
 */
export const PROGRESO_RELOJ = new InjectionToken<() => number>('PROGRESO_RELOJ', {
  factory: () => () => Date.now(),
});

/** Cada cuánto se refresca el cronómetro; en los tests no se espera un segundo real. */
export const PROGRESO_TICK_MS = new InjectionToken<number>('PROGRESO_TICK_MS', {
  factory: () => 1000,
});

/**
 * Avance real de la corrida (S2, S4).
 *
 * Muestra las fases que el backend ya cumplió, la que está corriendo con un
 * indicador animado y un cronómetro por fase. El conteo sale de `fase_desde` del
 * servidor: recargar la página no lo reinicia ni lo infla.
 *
 * Se mantiene como componente aparte porque su reloj es propio: la página no tiene
 * que re-renderizar el informe entero cada segundo.
 */
@Component({
  selector: 'app-progreso-corrida',
  imports: [NgIcon],
  viewProviders: [
    provideIcons({
      matCheckCircleOutline,
      matProgressActivityOutline,
      matRadioButtonUncheckedOutline,
    }),
  ],
  templateUrl: './progreso-corrida.html',
})
export class ProgresoCorrida implements OnDestroy {
  /** Fase actual de la corrida; `null` mientras el primer sondeo no llega. */
  readonly fase = input<string | null>(null);
  /** Marca ISO con zona en la que el backend entró en la fase actual (S4). */
  readonly faseDesde = input<string | null>(null);

  protected readonly fases = FASES_CORRIDA;
  protected readonly segundosDeEspera = MODELO_TARDA_SEGUNDOS;
  protected readonly indiceActual = computed(() => indiceDeFase(this.fase()));

  /**
   * Pulso del cronómetro: sólo cambia para que Angular vuelva a evaluar el tiempo
   * (y a dibujar los segundos nuevos). El instante sale del reloj inyectado, así un
   * reloj adelantado no produce valores negativos (el conteo se recorta en cero).
   */
  private readonly pulso = signal(0);
  private readonly reloj = inject(PROGRESO_RELOJ);
  private readonly tickMs = inject(PROGRESO_TICK_MS);
  private readonly intervalo = setInterval(
    () => this.pulso.update((valor) => valor + 1),
    this.tickMs,
  );

  protected readonly etiquetaActual = computed(() => {
    const indice = this.indiceActual();
    return indice < 0 ? '' : this.fases[indice].etiqueta;
  });

  /**
   * El cronómetro se evalúa en cada vuelta de detección de cambios (no es un
   * `computed`): su valor depende del reloj, que no es una señal. El pulso sólo
   * dispara esa evaluación.
   */
  protected cronometro(): string {
    this.pulso();
    return formatearSegundos(this.segundosEnFase());
  }

  protected esperaLarga(): boolean {
    this.pulso();
    return this.fase() === FASE_MODELO && this.segundosEnFase() >= ESPERA_LARGA_MODELO_SEGUNDOS;
  }

  ngOnDestroy(): void {
    clearInterval(this.intervalo);
  }

  protected estadoDe(indice: number): EstadoFase {
    const actual = this.indiceActual();
    if (actual < 0) return 'pendiente';
    if (indice < actual) return 'cumplida';
    return indice === actual ? 'actual' : 'pendiente';
  }

  /** Segundos desde que el backend entró en la fase, nunca negativos (S4). */
  private segundosEnFase(): number {
    const desde = this.faseDesde();
    if (desde === null) return 0;
    const inicio = Date.parse(desde);
    if (Number.isNaN(inicio)) return 0;
    return Math.max(0, Math.floor((this.reloj() - inicio) / 1000));
  }
}

/** `m:ss`: un cronómetro de espera, no una duración del informe. */
function formatearSegundos(total: number): string {
  const minutos = Math.floor(total / 60);
  const segundos = total % 60;
  return `${minutos}:${segundos.toString().padStart(2, '0')}`;
}
