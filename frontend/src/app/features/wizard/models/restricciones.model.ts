/** Energía disponible en la parcela: la declara el usuario, el agente no la elige. */
export type EnergiaDisponible = 'red-electrica' | 'solar';

export interface OpcionEnergia {
  value: EnergiaDisponible;
  label: string;
  detalle: string;
  icono: string;
}

export const ENERGIA_OPTIONS: readonly OpcionEnergia[] = [
  {
    value: 'red-electrica',
    label: 'Red eléctrica',
    detalle: 'Hay acometida en la parcela',
    icono: 'bolt',
  },
  {
    value: 'solar',
    label: 'Solar',
    detalle: 'Sin acometida: bomba solar',
    icono: 'solar_power',
  },
];

/** Tanque que el usuario ya tiene. `null` es "no tiene". */
export interface OpcionTanque {
  value: number | null;
  label: string;
}

export const TANQUE_OPTIONS: readonly OpcionTanque[] = [
  { value: null, label: 'No tiene' },
  { value: 2500, label: '2.500 L' },
  { value: 5000, label: '5.000 L' },
  { value: 10000, label: '10.000 L' },
];

/**
 * Piso del presupuesto informado.
 *
 * Sirve también para un jardín chico de patio, así que es bajo: por debajo de este monto
 * el agente no recibe el dato (un presupuesto de 1 Bs no es un presupuesto).
 */
export const PRESUPUESTO_MINIMO_BS = 100;

/** Restricciones del paso 3, tal como viajan al agente en el paso 4. */
export interface RestriccionesBorrador {
  energia: EnergiaDisponible;
  tanque_l: number | null;
  presupuesto_bs: number | null;
}

export const RESTRICCIONES_INICIALES: RestriccionesBorrador = {
  energia: 'red-electrica',
  tanque_l: null,
  presupuesto_bs: null,
};

/** Convierte lo que escribe el usuario en `null` o en un monto entero positivo. */
export function normalizarMonto(valor: string | number | null): number | null {
  if (valor === null) return null;
  if (typeof valor === 'string' && valor.trim() === '') return null;
  const monto = typeof valor === 'number' ? valor : Number(valor);
  if (!Number.isFinite(monto) || monto <= 0) return null;
  // Se trunca, no se redondea: 99.6 Bs sigue por debajo del piso y no debe pasar.
  return Math.floor(monto);
}
