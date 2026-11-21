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
    rol: 'cliente',
    activo: true,
    ultimo_acceso: null,
  },
};

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

  it('renders the credential fields disabled', async () => {
    const fixture = await render();

    for (const id of ['#fullName', '#workEmail', '#password', '#confirmPassword']) {
      const input = fixture.nativeElement.querySelector(id) as HTMLInputElement;
      expect(input).not.toBeNull();
      expect(input.disabled).toBe(true);
    }

    expect((fixture.nativeElement.querySelector('#userRole') as HTMLSelectElement).disabled).toBe(
      true,
    );
    expect((fixture.nativeElement.querySelector('#termsCheckbox') as HTMLInputElement).disabled).toBe(
      true,
    );
  });

  it('offers Google as the only way in and explains why', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.querySelector('app-google-sign-in')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('form')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain(
      'El backend todavía no acepta correo y contraseña.',
    );
  });

  it('creates the account through the register endpoint', async () => {
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

  it('shows the backend error and navigates nowhere when registration fails', async () => {
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
});
