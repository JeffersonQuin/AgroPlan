import { ParcelShape, TerrainDimensions, TerrainMetrics } from '../models/terrain.model';

/**
 * Reference geometry shown by the mockup on first load.
 *
 * The mockup's cotas are not consistent with its own summary: a 60 × 40 parcel
 * cannot hold 3,200 m² and the 42.40 m diagonal does not close the figure. The
 * reference values are kept so the screen matches the design, and are replaced
 * by `calculateMetrics` as soon as any cota changes.
 */
export const REFERENCE_METRICS: TerrainMetrics = {
  areaM2: 3200,
  perimeterM: 172.4,
  diagonalM: 42.4,
};

export const REFERENCE_DIMENSIONS: TerrainDimensions = {
  topM: 60,
  bottomM: 30,
  leftM: 40,
  rightM: 20,
};

/**
 * Closes the parcel as top → right side → diagonal → bottom → left side and
 * measures it with the shoelace formula.
 */
/** A vertex of the parcel, in metres, with the origin at the bottom-left corner. */
export interface Vertice { x: number; y: number; }

/**
 * Vertices the backend receives, for the chosen shape:
 *
 * - ``rectangulo`` — four sides from the top length and the left height;
 * - ``trapecio`` — the mockup's five-point figure, closed with a diagonal;
 * - ``libre`` — same figure as the trapezoid until the free drawing lands.
 *
 * It is the same figure ``calculateMetrics`` measures, so the area the API
 * returns matches what the wizard previewed.
 */
export function toVertices(
  { topM, bottomM, leftM, rightM }: TerrainDimensions,
  shape: ParcelShape,
): Vertice[] {
  const izquierda = Math.max(leftM, 0);
  const arriba = Math.max(topM, 0);

  if (shape === 'rectangulo') {
    return [
      { x: 0, y: 0 },
      { x: arriba, y: 0 },
      { x: arriba, y: izquierda },
      { x: 0, y: izquierda },
    ];
  }

  const derecha = Math.min(Math.max(rightM, 0), izquierda);
  const abajo = Math.max(bottomM, 0);

  return [
    { x: 0, y: izquierda },
    { x: arriba, y: izquierda },
    { x: arriba, y: izquierda - derecha },
    { x: abajo, y: 0 },
    { x: 0, y: 0 },
  ];
}

/**
 * Rebuilds the four cotas from a saved polygon, so re-entering step 1 shows the
 * parcel the user defined instead of the mockup reference.
 */
export function fromVertices(
  vertices: ReadonlyArray<{ x: number; y: number }>,
): TerrainDimensions | null {
  if (vertices.length === 4) {
    const alto = Math.max(...vertices.map((vertice) => vertice.y));
    const largo = Math.max(...vertices.map((vertice) => vertice.x));
    return { topM: largo, bottomM: largo, leftM: alto, rightM: alto };
  }

  if (vertices.length !== 5) return null;

  const ys = vertices.map((vertex) => vertex.y);
  const xs = vertices.map((vertex) => vertex.x);
  const arribaIzquierda = Math.max(...ys);
  const derechaArriba = vertices[2]?.y;

  return {
    topM: Math.max(...xs),
    bottomM: vertices[3]?.x ?? 0,
    leftM: arribaIzquierda,
    rightM: Number.isFinite(derechaArriba) ? arribaIzquierda - derechaArriba : 0,
  };
}

export function calculateMetrics(
  { topM, bottomM, leftM, rightM }: TerrainDimensions,
  shape: ParcelShape = 'trapecio',
) {
  if (shape === 'rectangulo') {
    const largo = Math.max(topM, 0);
    const alto = Math.max(leftM, 0);
    return {
      areaM2: round(largo * alto, 2),
      perimeterM: round(2 * (largo + alto), 2),
      diagonalM: round(Math.hypot(largo, alto), 2),
    };
  }

  const left = Math.max(leftM, 0);
  const right = Math.max(rightM, 0);
  const top = Math.max(topM, 0);
  const bottom = Math.max(bottomM, 0);

  // Origin at the bottom-left corner, x to the right, y upwards.
  const points: Array<[number, number]> = [
    [0, left],
    [top, left],
    [top, left - right],
    [bottom, 0],
    [0, 0],
  ];

  const areaM2 = Math.abs(shoelace(points)) / 2;
  const diagonalM = Math.hypot(top - bottom, right);
  const perimeterM = top + right + diagonalM + bottom + left;

  return {
    areaM2: round(areaM2, 2),
    perimeterM: round(perimeterM, 2),
    diagonalM: round(diagonalM, 2),
  };
}

/** Area of any polygon in square metres, by the shoelace formula. */
export function areaPoligono(vertices: ReadonlyArray<Vertice>): number {
  let suma = 0;
  for (let indice = 0; indice < vertices.length; indice++) {
    const actual = vertices[indice];
    const siguiente = vertices[(indice + 1) % vertices.length];
    suma += actual.x * siguiente.y - siguiente.x * actual.y;
  }
  return Math.abs(suma) / 2;
}

/**
 * True when two non-adjacent sides cross. With the four cotas the figure cannot
 * self-intersect, but once vertices are dragged it can, and the backend would
 * happily compute a nonsense area.
 */
export function seAutoIntersecta(vertices: ReadonlyArray<Vertice>): boolean {
  const total = vertices.length;
  if (total < 4) return false;

  for (let i = 0; i < total; i++) {
    const a1 = vertices[i];
    const a2 = vertices[(i + 1) % total];
    for (let j = i + 1; j < total; j++) {
      // Lados consecutivos comparten un vértice: no cuentan.
      if (j === i || (j + 1) % total === i || (i + 1) % total === j) continue;
      if (seCruzan(a1, a2, vertices[j], vertices[(j + 1) % total])) return true;
    }
  }
  return false;
}

function seCruzan(a: Vertice, b: Vertice, c: Vertice, d: Vertice): boolean {
  const orientacion = (p: Vertice, q: Vertice, r: Vertice) =>
    (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);

  const d1 = orientacion(a, b, c);
  const d2 = orientacion(a, b, d);
  const d3 = orientacion(c, d, a);
  const d4 = orientacion(c, d, b);

  return ((d1 > 0) !== (d2 > 0)) && ((d3 > 0) !== (d4 > 0));
}

/**
 * Cotas que cambian al arrastrar un vértice hasta (x, y) en metros.
 *
 * El vértice del origen no se mueve: trasladar la parcela no cambia el terreno.
 * Todo lo que devuelve está clampeado a cero o más.
 */
export function cotasDesdeArrastre(
  shape: ParcelShape,
  dimensions: TerrainDimensions,
  indice: number,
  x: number,
  y: number,
): Partial<TerrainDimensions> {
  const largo = Math.max(0, x);
  const alto = Math.max(0, y);

  if (shape === 'rectangulo') {
    // (0,0) (largo,0) (largo,alto) (0,alto)
    if (indice === 1) return { topM: largo, bottomM: largo };
    if (indice === 2) return { topM: largo, bottomM: largo, leftM: alto, rightM: alto };
    if (indice === 3) return { leftM: alto, rightM: alto };
    return {};
  }

  // (0,alto) (largo,alto) (largo,alto-derecho) (base,0) (0,0)
  if (indice === 0) return { leftM: alto };
  if (indice === 1) return { topM: largo };
  if (indice === 2) {
    const derecha = Math.max(0, Math.round((dimensions.leftM - alto) * 10) / 10);
    return { topM: largo, rightM: derecha };
  }
  if (indice === 3) return { bottomM: largo };
  return {};
}

/** Vertical drop of the parcel for a slope given in percent. */
export function calculateDesnivel(topM: number, slopePct: number): number {
  return round((Math.max(topM, 0) * Math.max(slopePct, 0)) / 100, 2);
}

function shoelace(points: ReadonlyArray<[number, number]>): number {
  let sum = 0;
  for (let index = 0; index < points.length; index++) {
    const [x1, y1] = points[index];
    const [x2, y2] = points[(index + 1) % points.length];
    sum += x1 * y2 - x2 * y1;
  }
  return sum;
}

function round(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}
