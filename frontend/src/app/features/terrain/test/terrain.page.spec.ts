import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { TerrainPage } from '../terrain.page';

const PROYECTO = {
  id: 'p-1',
  nombre: 'Los Olivos',
  zona: 'Valle Central',
  unidad: 'metric',
  estado: 'borrador',
  paso_actual: 1,
  ultimo_paso_completado: 0,
  version: 1,
  corrida_actual_id: null,
  creado_en: '2026-11-21T12:00:00',
  actualizado_en: '2026-11-21T12:00:00',
};

describe('TerrainPage', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'proyectos/:proyectoId/terreno', component: TerrainPage }]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('mounts step 1 for the project in the URL', async () => {
    const harness = await RouterTestingHarness.create('/proyectos/p-1/terreno');

    http.expectOne('http://localhost:8000/proyectos/p-1').flush(PROYECTO);
    http
      .expectOne('http://localhost:8000/proyectos/p-1/terreno')
      .flush({ detail: 'El proyecto todavía no tiene terreno' }, { status: 404, statusText: 'Not Found' });
    http.expectOne('http://localhost:8000/catalogos/suelos').flush([]);
    await harness.fixture.whenStable();

    const html = harness.routeNativeElement as HTMLElement;
    expect(html.querySelector('#parcela-nombre')).not.toBeNull();
    expect(html.textContent).toContain('Los Olivos');
    expect(html.textContent).toContain('Guardar y continuar a Cultivos');
    expect(html.textContent).toContain('Sin guardar');
  });
});
