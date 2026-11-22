import {
  calculateDesnivel,
  calculateMetrics,
  fromVertices,
  toVertices,
} from '../utils/terrain-geometry';

describe('terrain geometry', () => {
  it('measures the reference parcel from its cotas', () => {
    const metrics = calculateMetrics({ topM: 60, bottomM: 30, leftM: 40, rightM: 20 });

    expect(metrics.areaM2).toBe(2100);
    expect(metrics.diagonalM).toBe(36.06);
    expect(metrics.perimeterM).toBe(186.06);
  });

  it('measures a rectangle as top × height', () => {
    const metrics = calculateMetrics({ topM: 40, bottomM: 40, leftM: 25, rightM: 25 });

    expect(metrics.areaM2).toBe(1000);
    expect(metrics.diagonalM).toBe(25);
    expect(metrics.perimeterM).toBe(155);
  });

  it('clamps negative cotas to zero', () => {
    const metrics = calculateMetrics({ topM: -10, bottomM: -5, leftM: -2, rightM: -1 });

    expect(metrics.areaM2).toBe(0);
    expect(metrics.perimeterM).toBe(0);
  });

  it('derives the vertical drop from the slope', () => {
    expect(calculateDesnivel(60, 1)).toBe(0.6);
    expect(calculateDesnivel(60, 2.5)).toBe(1.5);
    expect(calculateDesnivel(60, 0)).toBe(0);
  });
});

describe('toVertices / fromVertices', () => {
  it('a rectangle only uses the top length and the left height', () => {
    const vertices = toVertices({ topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 'rectangulo');

    expect(vertices).toEqual([
      { x: 0, y: 0 },
      { x: 60, y: 0 },
      { x: 60, y: 40 },
      { x: 0, y: 40 },
    ]);
    expect(calculateMetrics({ topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 'rectangulo')).toEqual({
      areaM2: 2400,
      perimeterM: 200,
      diagonalM: 72.11,
    });
    expect(fromVertices(vertices)).toEqual({ topM: 60, bottomM: 60, leftM: 40, rightM: 40 });
  });

  it('builds the same five-vertex figure the preview measures', () => {
    const vertices = toVertices({ topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 'trapecio');

    expect(vertices).toEqual([
      { x: 0, y: 40 },
      { x: 60, y: 40 },
      { x: 60, y: 20 },
      { x: 30, y: 0 },
      { x: 0, y: 0 },
    ]);
  });

  it('rebuilds the cotas from a saved polygon', () => {
    const cotas = fromVertices(
      toVertices({ topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 'trapecio'),
    );

    expect(cotas).toEqual({ topM: 60, bottomM: 30, leftM: 40, rightM: 20 });
  });

  it('refuses a polygon it cannot map back to four cotas', () => {
    expect(fromVertices([{ x: 0, y: 0 }, { x: 1, y: 1 }, { x: 2, y: 0 }])).toBeNull();
  });
});
