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

  function boton(fixture: Awaited<ReturnType<typeof render>>, title: string): HTMLButtonElement {
    return Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((candidate) => candidate.title === title)!;
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

  it('draws exactly one hit area, halo and marker per vertex', async () => {
    const fixture = await render();

    const circulos = fixture.nativeElement.querySelectorAll(
      'svg[aria-label="Croquis del terreno"] > g circle',
    ) as NodeListOf<SVGCircleElement>;
    expect(circulos.length).toBe(store.vertices().length * 3);
  });

  it('centers the figure in the frame', async () => {
    const fixture = await render();

    const poligono = fixture.nativeElement.querySelector(
      'g#figura polygon:last-of-type, polygon',
    ) as SVGPolygonElement;
    const puntos = poligono
      .getAttribute('points')!
      .split(' ')
      .map((par) => par.split(',').map(Number));
    const xs = puntos.map(([x]) => x);
    const ys = puntos.map(([, y]) => y);

    expect((Math.min(...xs) + Math.max(...xs)) / 2).toBeCloseTo(370, 0);
    expect((Math.min(...ys) + Math.max(...ys)) / 2).toBeCloseTo(245, 0);
  });

  it('shows the grid by default and toggles it', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.querySelector('rect[fill="url(#cuadricula)"]')).not.toBeNull();

    boton(fixture, 'Ocultar cuadrícula').click();
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelector('rect[fill="url(#cuadricula)"]')).toBeNull();
  });

  it('zooms in and out and recenters', async () => {
    const fixture = await render();
    const figura = fixture.nativeElement.querySelector(
      'svg[aria-label="Croquis del terreno"] > g',
    ) as SVGGElement;

    expect(figura.getAttribute('transform')).toContain('scale(1.000)');

    boton(fixture, 'Zoom +').click();
    await fixture.whenStable();
    expect(figura.getAttribute('transform')).toContain('scale(1.250)');

    boton(fixture, 'Zoom −').click();
    boton(fixture, 'Zoom −').click();
    await fixture.whenStable();
    expect(figura.getAttribute('transform')).toContain('scale(0.800)');

    boton(fixture, 'Centrar la figura').click();
    await fixture.whenStable();
    expect(figura.getAttribute('transform')).toContain('scale(1.000)');
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
