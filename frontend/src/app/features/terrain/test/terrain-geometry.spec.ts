import { calculateDesnivel, calculateMetrics } from '../utils/terrain-geometry';

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
