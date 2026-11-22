/**
 * Formato del informe: todo dato que falta se dice "no informado", nunca se
 * rellena con cero (S10).
 *
 * Los números se formatean sin separador de miles a propósito: el mismo texto es
 * el que se compara en el informe y el que va al PDF, y así no depende del ICU del
 * runtime.
 */

export const NO_INFORMADO = 'no informado';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** Número listo para mostrar; `null` es "no informado". */
export function formatearNumero(valor: number | null, decimales = 0): string {
  if (valor === null || !Number.isFinite(valor)) return NO_INFORMADO;
  const factor = 10 ** decimales;
  return String(Math.round(valor * factor) / factor);
}

/** Número con su unidad en el mismo texto; `null` sigue siendo "no informado". */
export function formatearConUnidad(
  valor: number | null,
  unidad: string,
  decimales = 0,
): string {
  if (valor === null || !Number.isFinite(valor)) return NO_INFORMADO;
  return `${formatearNumero(valor, decimales)} ${unidad}`;
}

/** Fecha `YYYY-MM-DD` (o ISO con hora) como "15 mar 2026"; sin fecha, "no informado". */
export function formatearFecha(fecha: string | null): string {
  if (fecha === null || fecha.length < 10) return NO_INFORMADO;
  const [anio, mes, dia] = fecha.slice(0, 10).split('-').map(Number);
  if (!Number.isFinite(anio) || !Number.isFinite(mes) || !Number.isFinite(dia)) {
    return NO_INFORMADO;
  }
  if (mes < 1 || mes > 12) return NO_INFORMADO;
  return `${dia} ${MESES[mes - 1]} ${anio}`;
}

/** Área del terreno en hectáreas, o `null` si no vino. */
export function aHectareas(areaM2: number | null): number | null {
  if (areaM2 === null || !Number.isFinite(areaM2)) return null;
  return Math.round((areaM2 / 10000) * 100) / 100;
}

/** Etiqueta legible de un campo del motor que el agente propuso distinto. */
export function etiquetaCampoAjuste(campo: string): string {
  const etiquetas: Record<string, string> = {
    presion_trabajo_bar: 'Presión de trabajo',
    caudal_sector_m3h: 'Caudal por sector',
    tiempo_riego_h: 'Tiempo de riego',
    autonomia_dias: 'Autonomía del tanque',
    demanda_pico_l_dia: 'Demanda pico',
    eficiencia_pct: 'Eficiencia',
    num_sectores: 'Cantidad de sectores',
    tuberia_m: 'Tubería',
    goteros_u: 'Goteros',
    valvulas_u: 'Válvulas',
  };
  return etiquetas[campo] ?? campo.replace(/_/g, ' ');
}

/** Tipo de sistema de riego del motor en castellano. */
export function textoSistema(tipo: string): string {
  const textos: Record<string, string> = {
    goteo: 'Goteo localizado',
    aspersion: 'Aspersión',
    inundacion: 'Inundación',
  };
  return textos[tipo] ?? tipo;
}

/** Tipo de emisor del motor en castellano. */
export function textoEmisor(tipo: string): string {
  const textos: Record<string, string> = {
    gotero: 'Gotero',
    microaspersor: 'Microaspersor',
    aspersor: 'Aspersor',
  };
  return textos[tipo] ?? tipo;
}

/** Material de la tubería según el tipo de tramo, para la leyenda del plano. */
export function materialTramo(tipo: string): string {
  const materiales: Record<string, string> = {
    principal: 'PVC',
    secundario: 'PVC',
    lateral: 'PE',
    conexion: 'Conexión',
  };
  return materiales[tipo] ?? 'Tubería';
}

/** Nombre del tramo en la leyenda. */
export function textoTramo(tipo: string): string {
  const textos: Record<string, string> = {
    principal: 'Tubería principal',
    secundario: 'Tubería secundaria',
    lateral: 'Lateral de goteo',
    conexion: 'Conexión',
  };
  return textos[tipo] ?? tipo;
}
