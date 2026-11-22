/** Contratos y modelos del paso 2 (cultivos), espejo de `app/schemas/cultivo.py`. */

export type ModoReparto = 'porcentaje' | 'poligono';
export type EstadoBalance = 'correcto' | 'ajustado' | 'excedido';

export interface AdvertenciaApi {
  codigo: string;
  mensaje: string;
  bloqueante: boolean;
  campo: string | null;
}

export interface AptitudSueloApi {
  veredicto: 'apto' | 'condicionado' | 'no_apto';
  motivo: string | null;
  fuente: string | null;
}

/** Bloque de cultivo tal como lo devuelve la API, con sus derivados. */
export interface BloqueApi {
  id: string;
  cultivo_codigo: string;
  etiqueta: string | null;
  area_m2: number;
  poligono: { anillo: [number, number][] };
  siembra: string | null;
  cosecha: string | null;
  demanda_l_m2_dia: number;
  orden: number;
  origen: string;
  porcentaje: number;
  demanda_total_l_dia: number;
  ciclo_dias: number | null;
  kc: number | null;
  dias_a_cosecha: number | null;
  aptitud_suelo: AptitudSueloApi | null;
  advertencias: AdvertenciaApi[];
}

export interface CicloApi {
  cultivo_codigo: string;
  desde: string | null;
  hasta: string | null;
}

export interface SolapeApi {
  desde: string;
  hasta: string;
  cultivos: string[];
}

/** Panel derecho del paso 2: siempre completo, calculado por el backend. */
export interface BalanceApi {
  terreno_m2: number;
  asignado_m2: number;
  disponible_m2: number;
  estado: EstadoBalance;
  demanda_total_l_dia: number;
  demanda_prom_l_m2_dia: number;
  calendario: CicloApi[];
  solapes: SolapeApi[];
  alertas: AdvertenciaApi[];
}

/** `GET /catalogos/cultivos`. */
export interface CultivoCatalogoApi {
  codigo: string;
  nombre: string;
  icono: string;
  color: string;
  demanda_agua_l_m2_dia: number;
  ciclo_dias: number;
  kc: number | null;
  densidad_plantas_m2: number | null;
  profundidad_raiz_cm: number | null;
  meses_siembra: number[] | null;
  activo: boolean;
}

/** `POST /proyectos/{id}/cultivos`. */
export interface CrearBloqueApi {
  cultivo_codigo?: string;
  producto_texto?: string;
  etiqueta?: string | null;
  siembra?: string | null;
  cosecha?: string | null;
  demanda_l_m2_dia?: number | null;
  modo: ModoReparto;
  porcentaje?: number | null;
}

/** `PATCH /proyectos/{id}/cultivos/{bloque_id}`. */
export interface EditarBloqueApi {
  etiqueta?: string | null;
  siembra?: string | null;
  cosecha?: string | null;
  demanda_l_m2_dia?: number | null;
  porcentaje?: number | null;
}

/** `200`/`201` de cualquier escritura del paso 2. */
export interface CultivoRespuestaApi {
  bloque: BloqueApi;
  balance: BalanceApi;
  advertencias: AdvertenciaApi[];
}

/** Datos del terreno que el paso 2 muestra en la cabecera. */
export interface ResumenTerrenoApi {
  area_m2: number;
  caudal_efectivo_m3h: number;
  suelo_codigo: string;
}
