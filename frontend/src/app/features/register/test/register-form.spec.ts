import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { SESSION_STORAGE_KEY, TokenResponse } from '../../auth/auth.model';
import { RegisterForm } from '../components/register-form/register-form';

const TOKEN_RESPONSE: TokenResponse = {
  access_token: 'jwt-token',
  token_type: 'bearer',
  usuario: {
    id: 9,
    email: 'nuevo@agroplan.com',
    nombre: 'Ing. Nueva',
    foto_url: null,
    rol: 'agronomo',
    activo: true,
    ultimo_acceso: null,
  },
};

const REGISTER_URL = 'http://localhost:8000/auth/register';

describe('RegisterForm', () => {
  let http: HttpTestingController;
  let navigations: string[];

  beforeEach(async () => {
    localStorage.clear();
    navigations = [];
    await TestBed.configureTestingModule({
      imports: [RegisterForm],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({}) } },
        },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
    vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockImplementation((url) => {
      navigations.push(url.toString());
      return Promise.resolve(true);
    });
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  async function render() {
    const fixture = TestBed.createComponent(RegisterForm);
    await fixture.whenStable();
    return fixture;
  }

  it('creates the account with email and password', async () => {
    const fixture = await render();

    expect((fixture.nativeElement.querySelector('#fullName') as HTMLInputElement).disabled).toBe(
      false,
    );
    expect((fixture.nativeElement.querySelector('#workEmail') as HTMLInputElement).disabled).toBe(
      false,
    );
    expect((fixture.nativeElement.querySelector('#password') as HTMLInputElement).disabled).toBe(
      false,
    );
    expect(
      (fixture.nativeElement.querySelector('#confirmPassword') as HTMLInputElement).disabled,
    ).toBe(false);
    expect((fixture.nativeElement.querySelector('#userRole') as HTMLSelectElement).disabled).toBe(
      false,
    );
    expect(
      (fixture.nativeElement.querySelector('#termsCheckbox') as HTMLInputElement).disabled,
    ).toBe(false);

    await fill(fixture, '#fullName', '  Ing. Nueva  ');
    await fill(fixture, '#workEmail', '  nuevo@agroplan.com  ');
    await select(fixture, '#userRole', 'agronomo');
    await fill(fixture, '#password', 'secreto-2026');
    await fill(fixture, '#confirmPassword', 'secreto-2026');
    await check(fixture, '#termsCheckbox');
    await submit(fixture);

    const request = http.expectOne(REGISTER_URL);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      nombre: 'Ing. Nueva',
      email: 'nuevo@agroplan.com',
      password: 'secreto-2026',
      rol: 'agronomo',
    });
    request.flush(TOKEN_RESPONSE);
    await fixture.whenStable();

    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toContain('jwt-token');
    expect(navigations).toEqual(['/projects']);
  });

  it('rejects an empty submit before calling the API', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.textContent).not.toContain('Ingresá tu nombre completo.');

    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain('Ingresá tu nombre completo.');
    expect(fixture.nativeElement.textContent).toContain('Ingresá tu correo profesional.');
    expect(fixture.nativeElement.textContent).toContain('Seleccioná tu rol o especialidad.');
    expect(fixture.nativeElement.textContent).toContain('Ingresá una contraseña.');
    expect(fixture.nativeElement.textContent).toContain('Repetí tu contraseña.');
    expect(fixture.nativeElement.textContent).toContain(
      'Tenés que aceptar los términos para crear tu cuenta.',
    );

    http.expectNone(REGISTER_URL);
    expect(navigations).toEqual([]);
  });

  it('rejects a malformed email and a short password before calling the API', async () => {
    const fixture = await render();

    await fill(fixture, '#fullName', 'Ing. Nueva');
    await fill(fixture, '#workEmail', 'no-es-un-correo');
    await select(fixture, '#userRole', 'agronomo');
    await fill(fixture, '#password', 'corta');
    await fill(fixture, '#confirmPassword', 'corta');
    await check(fixture, '#termsCheckbox');
    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain('Ese correo no parece válido.');
    expect(fixture.nativeElement.textContent).toContain(
      'La contraseña necesita al menos 8 caracteres.',
    );
    http.expectNone(REGISTER_URL);
    expect(navigations).toEqual([]);
  });

  it('blocks the submit when the confirmation does not match the password', async () => {
    const fixture = await render();

    await fill(fixture, '#fullName', 'Ing. Nueva');
    await fill(fixture, '#workEmail', 'nuevo@agroplan.com');
    await select(fixture, '#userRole', 'agronomo');
    await fill(fixture, '#password', 'secreto-2026');
    await fill(fixture, '#confirmPassword', 'secreto-2025');
    await check(fixture, '#termsCheckbox');
    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain('Las contraseñas no coinciden.');
    http.expectNone(REGISTER_URL);
    expect(navigations).toEqual([]);
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it('shows the backend error and navigates nowhere when registration fails', async () => {
    const fixture = await render();

    await fill(fixture, '#fullName', 'Ing. Nueva');
    await fill(fixture, '#workEmail', 'nuevo@agroplan.com');
    await select(fixture, '#userRole', 'agronomo');
    await fill(fixture, '#password', 'secreto-2026');
    await fill(fixture, '#confirmPassword', 'secreto-2026');
    await check(fixture, '#termsCheckbox');
    await submit(fixture);

    http
      .expectOne(REGISTER_URL)
      .flush(
        { detail: 'Ya existe una cuenta con ese correo' },
        { status: 409, statusText: 'Conflict' },
      );
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Ya existe una cuenta con ese correo');
    expect(navigations).toEqual([]);
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it('renders Google before the credential fields', async () => {
    const fixture = await render();
    const google = fixture.nativeElement.querySelector('app-google-sign-in');
    const form = fixture.nativeElement.querySelector('form');

    expect(google).not.toBeNull();
    expect(form).not.toBeNull();
    expect(google.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('creates the account through the Google register endpoint', async () => {
    const fixture = await render();

    fixture.componentInstance['onCredential']('google-id-token');

    const request = http.expectOne('http://localhost:8000/auth/google/register');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ id_token: 'google-id-token' });
    request.flush(TOKEN_RESPONSE);
    await fixture.whenStable();

    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toContain('jwt-token');
    expect(navigations).toEqual(['/projects']);
  });

  it('shows the backend error when the Google exchange fails', async () => {
    const fixture = await render();

    fixture.componentInstance['onCredential']('bad-token');
    http
      .expectOne('http://localhost:8000/auth/google/register')
      .flush({ detail: 'Token de Google inválido' }, { status: 401, statusText: 'Unauthorized' });
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Token de Google inválido');
    expect(navigations).toEqual([]);
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it('keeps the switch back to login visible in the header', async () => {
    const fixture = await render();
    const nav = fixture.nativeElement.querySelector('app-auth-nav');

    expect(nav).not.toBeNull();
    expect(nav.textContent).toContain('Iniciar Sesión');
    expect(nav.textContent).toContain('Crear Cuenta');
    expect(nav.querySelector('a[href="/login"]')).not.toBeNull();
    expect(nav.querySelector('[aria-current="page"]').textContent).toContain('Crear Cuenta');
  });

  it('still offers the login link in the footer', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.textContent).toContain('¿Ya tienes una cuenta activa?');
    expect(fixture.nativeElement.querySelector('a[href="/login"]')).not.toBeNull();
  });

  it('renders an inline SVG for each of the four field icons', async () => {
    const fixture = await render();
    const icons = Array.from(
      fixture.nativeElement.querySelectorAll(
        'app-register-field ng-icon',
      ) as NodeListOf<HTMLElement>,
    );

    expect(icons.length).toBe(4);
    expect(icons.filter((icon) => icon.querySelector('svg') === null).length).toBe(0);
  });
});

interface Fixture {
  nativeElement: HTMLElement;
  whenStable: () => Promise<unknown>;
}

async function fill(fixture: Fixture, selector: string, value: string): Promise<void> {
  const input = fixture.nativeElement.querySelector(selector) as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await fixture.whenStable();
}

async function select(fixture: Fixture, selector: string, value: string): Promise<void> {
  const control = fixture.nativeElement.querySelector(selector) as HTMLSelectElement;
  control.value = value;
  control.dispatchEvent(new Event('input'));
  await fixture.whenStable();
}

async function check(fixture: Fixture, selector: string): Promise<void> {
  const checkbox = fixture.nativeElement.querySelector(selector) as HTMLInputElement;
  checkbox.click();
  checkbox.dispatchEvent(new Event('input'));
  await fixture.whenStable();
}

async function submit(fixture: Fixture): Promise<void> {
  fixture.nativeElement
    .querySelector('form')!
    .dispatchEvent(new Event('submit', { cancelable: true }));
  await fixture.whenStable();
}
