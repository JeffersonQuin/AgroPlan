/**
 * Contratos del paso 4 (informe), espejo de `ResultadoProyectoOut` y `DisenoGenerado`
 * en `backend/app/schemas/agente.py` y `backend/app/schemas/riego.py`.
 *
 * El informe no calcula nada: pinta lo que el agente decidió y el motor ya grabó. Por
 * eso `null` es un valor con significado —"no informado"— y nunca se convierte en cero.
 */

import { AdvertenciaApi } from '../../cultivos/models/cultivos.model';
import { EstadoProyectoApi } from '../../projects/models/project.model';

export interface PuntoInformeApi {
  x: number;
  y: number;
}

/** Anillo cerrado en metros: `[x, y]` como los devuelve el backend. */
export interface PoligonoInformeApi {
  anillo: [number, number][];
}

/** Bloque de cultivo con su polígono listo para pintar (S1). */
export interface BloqueInformeApi {
  id: string;
  cultivo_codigo: string;
  color: string;
  poligono: PoligonoInformeApi;
  area_m2: number;
  centroide: PuntoInformeApi;
  nombre: string | null;
  porcentaje: number | null;
  demanda_pico_l_dia: number | null;
  siembra: string | null;
  cosecha: string | null;
  ciclo_dias: number | null;
  kc: number | null;
  /** Imagen del agente o de la ficha curada; `null` deja el placeholder (S4). */
  imagen_url: string | null;
  imagen_credito: string | null;
}

export interface EmisorSistemaApi {
  tipo: string;
  caudal_lh: number;
  separacion_m: number;
}

export interface SistemaInformeApi {
  id: string;
  tipo: string;
  fuente_agua: string;
  tanque_l: number | null;
  bomba_hp: number;
  diametro_principal_mm: number;
  emisor: EmisorSistemaApi;
  separacion_laterales_m: number;
  orientacion: string;
  punto_conexion: PuntoInformeApi;
  num_sectores: number;
  red_generada_en: string | null;
  parametros_version: number;
}

export interface SectorInformeApi {
  id: string;
  numero: number;
  etiqueta: string | null;
  poligono: PoligonoInformeApi;
  area_m2: number;
  num_goteros: number;
  caudal_m3h: number;
  secuencia: number;
  cultivo_ids: string[];
}

export interface TramoRedApi {
  id: string;
  sector_id: string | null;
  tipo: string;
  diametro_mm: number;
  longitud_m: number;
  caudal_m3h: number | null;
  orden: number;
  puntos: [number, number][];
}

export interface NodoRedApi {
  id: string;
  tipo: string;
  geometria: PuntoInformeApi;
  tramo_id: string | null;
  atributos: Record<string, unknown> | null;
}

export interface EmisoresTramoApi {
  tramo_id: string;
  separacion_m: number;
  puntos: [number, number][];
}

/** Red completa: el plano 2D sale de acá, nunca de coordenadas inventadas (S10). */
export interface RedInformeApi {
  nodos: NodoRedApi[];
  tramos: TramoRedApi[];
  emisores: EmisoresTramoApi[];
}

/** Cómputo del motor: sólo lo que calcula la red. */
export interface ComputoInformeApi {
  tuberia_m: number;
  goteros_u: number;
  valvulas_u: number;
}

/** Cifras hidráulicas del motor (S9). `null` es "no informado". */
export interface CifrasMotorApi {
  presion_trabajo_bar: number | null;
  caudal_sector_m3h: number | null;
  tiempo_riego_h: number | null;
  autonomia_dias: number | null;
  demanda_pico_l_dia: number | null;
}

export interface TurnoSectorApi {
  sector: number;
  horas: number | null;
  caudal_lh: number | null;
}

/** Balance hidráulico y operativo que decidió el agente (S3). */
export interface CifrasAgenteApi {
  presion_trabajo_bar: number | null;
  eficiencia_pct: number | null;
  demanda_pico_l_dia: number | null;
  autonomia_dias: number | null;
  tiempo_riego_h: number | null;
  turnos: TurnoSectorApi[];
}

/** Diferencia entre la propuesta del agente y lo que hizo el motor (S3). */
export interface AjusteMotorApi {
  campo: string;
  valor_agente: string | null;
  valor_motor: string | null;
  motivo: string;
}

export interface CalendarioBloqueApi {
  bloque_id: string;
  cultivo_codigo: string;
  etiqueta: string | null;
  siembra: string | null;
  cosecha: string | null;
}

/** Rubro del cómputo con su precio y su fuente (S6). */
export interface MaterialInformeApi {
  rubro: string;
  descripcion: string;
  cantidad: number;
  unidad: string;
  moneda: string;
  precio_unitario_bs: number | null;
  total_bs: number | null;
  fuente_url: string | null;
  recuperado_en: string | null;
  reutilizado: boolean;
}

export interface RecomendacionInformeApi {
  id: string | null;
  tipo: string;
  titulo: string;
  detalle: string | null;
  justificacion: string | null;
  aplicada: boolean | null;
}

export interface FuenteInformeApi {
  id: string;
  tipo: string;
  titulo: string | null;
  url: string | null;
  fragmento: string | null;
  recuperado_en: string;
}

/** Salida completa del motor: lo que pinta el informe y consume el PDF. */
export interface DisenoInformeApi {
  bloques: BloqueInformeApi[];
  sistema: SistemaInformeApi;
  sectores: SectorInformeApi[];
  red: RedInformeApi;
  computo: ComputoInformeApi;
  advertencias: AdvertenciaApi[];
  cifras: CifrasMotorApi;
  cifras_agente: CifrasAgenteApi | null;
  eficiencia_pct: number | null;
  calendario: CalendarioBloqueApi[];
  materiales: MaterialInformeApi[];
  presupuesto_bs: number | null;
  costo_total_bs: number | null;
  presupuesto_excedido: boolean | null;
  recomendaciones: RecomendacionInformeApi[];
  fuentes: FuenteInformeApi[];
  ajustes: AjusteMotorApi[];
}

/** `GET /proyectos/{id}/resultado`: documento de sólo lectura del paso 4. */
export interface ResultadoProyectoApi {
  proyecto_id: string;
  nombre: string;
  estado: EstadoProyectoApi;
  diseno: DisenoInformeApi;
  advertencias: AdvertenciaApi[];
}

/** Producto del borrador listo para el modal de resumen previo (S2). */
export interface ProductoResumen {
  etiqueta: string;
  /** Inicial del placeholder cuando no hay imagen (S4). */
  inicial: string;
  color: string;
  imagenUrl: string | null;
  imagenCredito: string | null;
}

/** Terreno del modal: lo que el paso 1 ya cargó. */
export interface TerrenoResumen {
  nombre: string;
  areaM2: number;
  sueloCodigo: string;
  sueloNombre: string;
  fuenteLabel: string;
  caudalM3h: number;
  /** Pendiente del paso 1; `null` cuando el terreno no la informó. */
  pendientePct: number | null;
}

/** Restricciones del paso 3 tal como se muestran antes de generar. */
export interface RestriccionesResumen {
  energiaLabel: string;
  tanqueL: number | null;
  presupuestoBs: number | null;
  presupuestoBajoElPiso: boolean;
  presupuestoMinimoBs: number;
}
