import { TerrainDimensions, TerrainMetrics } from '../models/terrain.model';

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
/**
 * Vertices the backend receives: the same figure `calculateMetrics` measures, so
 * the area the API returns matches what the wizard previewed.
 */
export function toVertices({ topM, bottomM, leftM, rightM }: TerrainDimensions) {
  const left = Math.max(leftM, 0);
  const right = Math.min(Math.max(rightM, 0), left);
  const top = Math.max(topM, 0);
  const bottom = Math.max(bottomM, 0);

  return [
    { x: 0, y: left },
    { x: top, y: left },
    { x: top, y: left - right },
    { x: bottom, y: 0 },
    { x: 0, y: 0 },
  ];
}

/**
 * Rebuilds the four cotas from a saved polygon, so re-entering step 1 shows the
 * parcel the user defined instead of the mockup reference.
 */
export function fromVertices(vertices: ReadonlyArray<{ x: number; y: number }>): TerrainDimensions | null {
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

export function calculateMetrics({ topM, bottomM, leftM, rightM }: TerrainDimensions) {
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
