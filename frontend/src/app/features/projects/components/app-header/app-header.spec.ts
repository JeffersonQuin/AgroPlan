import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { BackendUser, SESSION_STORAGE_KEY } from '../../../auth/auth.model';
import { AuthStore } from '../../../auth/auth.store';
import { AppHeader } from './app-header';

const USUARIO: BackendUser = {
  id: 7,
  email: 'lucia@agroplan.com',
  nombre: 'Lucía Fernández',
  foto_url: null,
  rol: 'cliente',
  activo: true,
  ultimo_acceso: null,
};

const SESION = { token: 'jwt-token', user: USUARIO };

describe('AppHeader', () => {
  let http: HttpTestingController;
  let router: Router;
  let navegaciones: unknown[][];

  beforeEach(async () => {
    localStorage.clear();
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(SESION));

    await TestBed.configureTestingModule({
      imports: [AppHeader],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    http = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    navegaciones = [];
    router.navigate = ((comandos: unknown[]) => {
      navegaciones.push(comandos);
      return Promise.resolve(true);
    }) as Router['navigate'];
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  async function render(): Promise<ComponentFixture<AppHeader>> {
    const fixture = TestBed.createComponent(AppHeader);
    await fixture.whenStable();
    return fixture;
  }

  function text(fixture: ComponentFixture<AppHeader>): string {
    return fixture.nativeElement.textContent as string;
  }

  function desplegable(fixture: ComponentFixture<AppHeader>): HTMLButtonElement | null {
    return fixture.nativeElement.querySelector('button[aria-haspopup="menu"]');
  }

  function opciones(fixture: ComponentFixture<AppHeader>): HTMLButtonElement[] {
    return Array.from(
      fixture.nativeElement.querySelectorAll('[role="menuitem"]') as NodeListOf<HTMLButtonElement>,
    );
  }

  it('drops the primary navigation and the notification bell', async () => {
    const fixture = await render();
    const contenido = text(fixture);

    expect(fixture.nativeElement.querySelector('nav')).toBeNull();
    expect(contenido).not.toContain('Mis Proyectos');
    expect(contenido).not.toContain('Catálogo de Cultivos');
    expect(contenido).not.toContain('Calculadora Hidráulica');
    expect(contenido).not.toContain('Documentación');
    expect(fixture.nativeElement.querySelector('[aria-label="Notificaciones"]')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('a[href="#"]').length).toBe(0);
  });

  it('links the brand to /projects', async () => {
    const fixture = await render();
    const marca = fixture.nativeElement.querySelector('header a') as HTMLAnchorElement;

    expect(marca).not.toBeNull();
    expect(marca.getAttribute('href')).toBe('/projects');
    expect(marca.getAttribute('aria-label')).toContain('AgroPlan');
    expect(marca.textContent).toContain('AgroPlan');
  });

  it('shows the session name, its initials and the session role', async () => {
    const fixture = await render();
    const contenido = text(fixture);
    const iniciales = desplegable(fixture)?.querySelector('span[aria-hidden="true"]');

    expect(contenido).toContain('Lucía Fernández');
    expect(contenido).toContain('cliente');
    expect(contenido).not.toContain('Ing. Martín Rossi');
    expect(contenido).not.toContain('Agrónomo Senior');
    expect(iniciales?.textContent?.trim()).toBe('LF');
  });

  it('falls back without a menu when the session has no user', async () => {
    localStorage.clear();
    const fixture = await render();
    const contenido = text(fixture);

    expect(desplegable(fixture)).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('[role="menuitem"]').length).toBe(0);
    expect(contenido).toContain('Invitado');
    expect(contenido).toContain('Sin sesión');
  });

  it('opens the account menu and logs out from it', async () => {
    const fixture = await render();
    const disparador = desplegable(fixture)!;

    expect(disparador.getAttribute('aria-expanded')).toBe('false');
    expect(text(fixture)).not.toContain('Cerrar sesión');

    disparador.click();
    await fixture.whenStable();

    expect(disparador.getAttribute('aria-expanded')).toBe('true');
    expect(text(fixture)).toContain('Cerrar sesión');

    const salir = opciones(fixture).find((opcion) =>
      opcion.textContent?.includes('Cerrar sesión'),
    )!;
    salir.click();
    await fixture.whenStable();

    expect(TestBed.inject(AuthStore).user()).toBeNull();
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    expect(navegaciones).toEqual([['/login']]);
    expect(fixture.nativeElement.querySelectorAll('[role="menuitem"]').length).toBe(0);
    expect(text(fixture)).toContain('Invitado');
  });

  it('closes the menu on Escape or on a click outside the trigger', async () => {
    const fixture = await render();

    desplegable(fixture)!.click();
    await fixture.whenStable();
    expect(text(fixture)).toContain('Cerrar sesión');

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelectorAll('[role="menuitem"]').length).toBe(0);

    desplegable(fixture)!.click();
    await fixture.whenStable();
    expect(text(fixture)).toContain('Cerrar sesión');

    document.body.click();
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelectorAll('[role="menuitem"]').length).toBe(0);
  });

  it('keeps the new project action and the online pill', async () => {
    const fixture = await render();
    const contenido = text(fixture);
    let emitido = false;

    fixture.componentInstance.newProject.subscribe(() => (emitido = true));
    const nuevo = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((boton) => boton.textContent?.includes('Nuevo proyecto'))!;

    nuevo.click();

    expect(emitido).toBe(true);
    expect(contenido).toContain('En línea');
  });
});
