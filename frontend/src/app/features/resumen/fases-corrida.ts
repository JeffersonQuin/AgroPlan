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

/**
 * Sub-fase real del modelo: el segundo intento, cuando el primero no validó.
 *
 * No agrega un paso al stepper (`FASES_CORRIDA` no crece): se muestra dentro del
 * paso del modelo, que es donde de verdad está pasando. El backend la marca sólo
 * cuando arranca el reintento.
 */
export const FASE_MODELO_REINTENTO = 'modelo_reintento';

/**
 * Cómo se ve una sub-fase sin abrir un paso nuevo.
 *
 * `fase` es el paso del stepper al que pertenece; `etiqueta` y `fallo` son suyos
 * porque son más específicos que los del paso.
 */
const SUBFASES: ReadonlyMap<string, FaseEnPantalla> = new Map([
  [
    FASE_MODELO_REINTENTO,
    {
      fase: FASE_MODELO,
      etiqueta: 'Reintentando la consulta al modelo',
      fallo: 'reintentaba la consulta al modelo',
    },
  ],
]);

/** Pasados estos segundos en la fase del modelo se explica la espera larga (S2). */
export const ESPERA_LARGA_MODELO_SEGUNDOS = 20;

/** Datos medidos de una corrida real: el modelo tarda uno o dos minutos (S2). */
export const MODELO_TARDA_SEGUNDOS = 90;

const FASES_POR_NOMBRE = new Map<string, FaseEnPantalla>(
  FASES_CORRIDA.map((fase) => [fase.fase, fase]),
);

/** El paso del stepper al que pertenece una fase o sub-fase. */
function pasoDe(fase: string | null | undefined): string | null | undefined {
  if (fase === null || fase === undefined) return fase;
  return SUBFASES.get(fase)?.fase ?? fase;
}

/** Índice de la fase en el pipeline; `-1` cuando la corrida todavía no trae fase. */
export function indiceDeFase(fase: string | null | undefined): number {
  const paso = pasoDe(fase);
  return FASES_CORRIDA.findIndex((conocida) => conocida.fase === paso);
}

/** Etiqueta del paso actual; una sub-fase trae la suya, más específica. */
export function etiquetaDeFase(fase: string | null | undefined): string {
  if (fase === null || fase === undefined) return '';
  return SUBFASES.get(fase)?.etiqueta ?? FASES_POR_NOMBRE.get(fase)?.etiqueta ?? '';
}

/** ¿Es la fase del modelo, incluido su reintento? Es la espera larga real (S2). */
export function esFaseDelModelo(fase: string | null | undefined): boolean {
  return pasoDe(fase) === FASE_MODELO;
}

/**
 * Mensaje de una corrida fallada (S3): dice en qué fase quedó y suma el detalle
 * del backend. Sin fase conocida se conserva el mensaje de siempre.
 */
export function mensajeDeFallo(fase: string | null | undefined, detalle: string | null): string {
  const conocida =
    fase === null || fase === undefined
      ? undefined
      : (SUBFASES.get(fase) ?? FASES_POR_NOMBRE.get(fase));
  const limpio = detalle === null ? '' : detalle.trim();

  if (conocida === undefined) {
    return limpio === '' ? 'El agente no pudo generar el informe. Probá de nuevo.' : limpio;
  }

  const base = `El agente falló mientras ${conocida.fallo}.`;
  return limpio === '' ? base : `${base} ${limpio}`;
}
