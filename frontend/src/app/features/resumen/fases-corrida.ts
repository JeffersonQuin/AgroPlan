/**
 * Fases reales que ejecuta el backend durante una corrida del agente (S1, S2).
 *
 * Nada acá es decorativo ni un porcentaje estimado: cada fase se marca cuando el
 * backend realmente la empieza y el orden es el mismo del pipeline.
 */
export type FaseCorrida = 'contexto' | 'modelo' | 'validacion' | 'precios' | 'red' | 'listo';

export interface FaseEnPantalla {
  fase: FaseCorrida;
  /** Etiqueta de producto que ve el usuario en el stepper. */
  etiqueta: string;
  /** Cómo se nombra la fase cuando la corrida se rompe dentro de ella (S3). */
  fallo: string;
}

/** Las fases en el orden del backend: el stepper las muestra tal cual. */
export const FASES_CORRIDA: readonly FaseEnPantalla[] = [
  { fase: 'contexto', etiqueta: 'Preparando los datos', fallo: 'preparaba los datos' },
  { fase: 'modelo', etiqueta: 'Consultando al modelo', fallo: 'consultaba al modelo' },
  { fase: 'validacion', etiqueta: 'Validando la propuesta', fallo: 'validaba la propuesta' },
  { fase: 'precios', etiqueta: 'Calculando los precios', fallo: 'calculaba los precios' },
  { fase: 'red', etiqueta: 'Generando la red de riego', fallo: 'generaba la red de riego' },
  { fase: 'listo', etiqueta: 'Cerrando el informe', fallo: 'cerraba el informe' },
];

/** La fase larga: la del modelo es la que domina la espera (S2). */
export const FASE_MODELO: FaseCorrida = 'modelo';

/** Pasados estos segundos en la fase del modelo se explica la espera larga (S2). */
export const ESPERA_LARGA_MODELO_SEGUNDOS = 20;

/** Datos medidos de una corrida real: el modelo tarda uno o dos minutos (S2). */
export const MODELO_TARDA_SEGUNDOS = 90;

const FASES_POR_NOMBRE = new Map<string, FaseEnPantalla>(
  FASES_CORRIDA.map((fase) => [fase.fase, fase]),
);

/** Índice de la fase en el pipeline; `-1` cuando la corrida todavía no trae fase. */
export function indiceDeFase(fase: string | null | undefined): number {
  return FASES_CORRIDA.findIndex((conocida) => conocida.fase === fase);
}

/**
 * Mensaje de una corrida fallada (S3): dice en qué fase quedó y suma el detalle
 * del backend. Sin fase conocida se conserva el mensaje de siempre.
 */
export function mensajeDeFallo(fase: string | null | undefined, detalle: string | null): string {
  const conocida = fase === null || fase === undefined ? undefined : FASES_POR_NOMBRE.get(fase);
  const limpio = detalle === null ? '' : detalle.trim();

  if (conocida === undefined) {
    return limpio === '' ? 'El agente no pudo generar el informe. Probá de nuevo.' : limpio;
  }

  const base = `El agente falló mientras ${conocida.fallo}.`;
  return limpio === '' ? base : `${base} ${limpio}`;
}
