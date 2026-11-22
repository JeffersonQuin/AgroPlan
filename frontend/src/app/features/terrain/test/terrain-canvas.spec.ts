import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { TerrainCanvas } from '../components/terrain-canvas/terrain-canvas';
import { cotasDesdeArrastre } from '../utils/terrain-geometry';
import { TerrainStore } from '../state/terrain.store';

describe('TerrainCanvas', () => {
  let store: TerrainStore;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TerrainCanvas],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    store = TestBed.inject(TerrainStore);
  });

  async function render() {
    const fixture = TestBed.createComponent(TerrainCanvas);
    await fixture.whenStable();
    return fixture;
  }

  function lados(fixture: Awaited<ReturnType<typeof render>>): string[] {
    return Array.from(
      fixture.nativeElement.querySelectorAll('text') as NodeListOf<SVGTextElement>,
    ).map((texto) => texto.textContent?.trim() ?? '');
  }

  it('draws one label per side, with the length the backend will receive', async () => {
    const fixture = await render();

    expect(lados(fixture)).toEqual([
      '60.00 m',
      '20.00 m',
      '36.06 m',
      '30.00 m',
      '40.00 m',
    ]);
  });

  it('redraws when a cota changes', async () => {
    const fixture = await render();

    store.setDimension('topM', 80);
    await fixture.whenStable();

    expect(lados(fixture)[0]).toBe('80.00 m');
  });

  it('draws four sides for a rectangle', async () => {
    const fixture = await render();

    store.setShape('rectangulo');
    await fixture.whenStable();

    expect(lados(fixture)).toEqual(['60.00 m', '40.00 m', '60.00 m', '40.00 m']);
  });

  it('keeps the figure inside the drawing frame', async () => {
    const fixture = await render();

    const poligono = fixture.nativeElement.querySelector('polygon') as SVGPolygonElement;
    const puntos = poligono.getAttribute('points')!.split(' ').map((par) => par.split(',').map(Number));

    for (const [x, y] of puntos) {
      expect(x).toBeGreaterThanOrEqual(130);
      expect(x).toBeLessThanOrEqual(610);
      expect(y).toBeGreaterThanOrEqual(70);
      expect(y).toBeLessThanOrEqual(420);
    }
  });

  it('draws the living barrier along the figure', async () => {
    const fixture = await render();

    const circulos = fixture.nativeElement.querySelectorAll('circle') as NodeListOf<SVGCircleElement>;
    // Vértices + árboles: la barrera sigue a la figura.
    expect(circulos.length).toBeGreaterThan(store.vertices().length);
  });

  it('moving a vertex rewrites the cotas that define it', () => {
    expect(cotasDesdeArrastre('trapecio', { topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 1, 80, 40)).toEqual({
      topM: 80,
    });
    expect(cotasDesdeArrastre('trapecio', { topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 3, 45, 0)).toEqual({
      bottomM: 45,
    });
    expect(cotasDesdeArrastre('trapecio', { topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 2, 60, 25)).toEqual({
      topM: 60,
      rightM: 15,
    });
    // El vértice del origen no mueve nada.
    expect(cotasDesdeArrastre('trapecio', { topM: 60, bottomM: 30, leftM: 40, rightM: 20 }, 4, 5, 5)).toEqual({});

    expect(cotasDesdeArrastre('rectangulo', { topM: 60, bottomM: 60, leftM: 40, rightM: 40 }, 2, 70, 50)).toEqual({
      topM: 70,
      bottomM: 70,
      leftM: 50,
      rightM: 50,
    });
  });
});
