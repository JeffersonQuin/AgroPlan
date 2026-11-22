import { FuenteAguaApi } from '../../terrain/models/terrain.model';

/**
 * Lo que el paso 3 lee del terreno (paso 1): la fuente y el caudal ya están cargados
 * ahí, así que este paso no los vuelve a pedir.
 */
export interface TerrenoRiegoApi {
  area_m2: number;
  fuente_agua: FuenteAguaApi;
  caudal_disponible_m3h: number | null;
  caudal_efectivo_m3h: number;
}
