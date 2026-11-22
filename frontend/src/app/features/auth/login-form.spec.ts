import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { SESSION_STORAGE_KEY, TokenResponse } from './auth.model';
import { LoginForm } from './login-form';

const TOKEN_RESPONSE: TokenResponse = {
  access_token: 'jwt-token',
  token_type: 'bearer',
  usuario: {
    id: 7,
    email: 'agronomo@agroplan.com',
    nombre: null,
    foto_url: null,
    rol: 'cliente',
    activo: true,
    ultimo_acceso: null,
  },
};

describe('LoginForm', () => {
  let http: HttpTestingController;
  let navigations: string[];

  beforeEach(async () => {
    localStorage.clear();
    navigations = [];
    await TestBed.configureTestingModule({
      imports: [LoginForm],
      providers: [
        {
          provide: Router,
          useValue: {
            navigateByUrl: (url: string) => {
              navigations.push(url);
              return Promise.resolve(true);
            },
          },
        },
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ returnUrl: '/terreno' }) } },
        },
      ],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  async function render() {
    const fixture = TestBed.createComponent(LoginForm);
    await fixture.whenStable();
    return fixture;
  }

  it('lets the user sign in with email and password', async () => {
    const fixture = await render();

    expect(emailInput(fixture).disabled).toBe(false);
    expect(passwordInput(fixture).disabled).toBe(false);

    await fill(fixture, '#input-email', '  agronomo@agroplan.com  ');
    await fill(fixture, '#input-password', 'secreto-2026');
    await submit(fixture);

    const request = http.expectOne('http://localhost:8000/auth/login');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      email: 'agronomo@agroplan.com',
      password: 'secreto-2026',
    });
    request.flush(TOKEN_RESPONSE);
    await fixture.whenStable();

    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toContain('jwt-token');
    expect(navigations).toEqual(['/terreno']);
  });

  it('rejects an empty or malformed email before calling the API', async () => {
    const fixture = await render();

    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain('Ingresá tu correo profesional.');
    expect(fixture.nativeElement.textContent).toContain('Ingresá tu contraseña.');

    await fill(fixture, '#input-email', 'no-es-un-correo');
    await fill(fixture, '#input-password', 'secreto-2026');
    await submit(fixture);

    expect(fixture.nativeElement.textContent).toContain('Ese correo no parece válido.');
    http.expectNone('http://localhost:8000/auth/login');
    expect(navigations).toEqual([]);
  });

  it('shows the backend error when the credentials are rejected', async () => {
    const fixture = await render();

    await fill(fixture, '#input-email', 'agronomo@agroplan.com');
    await fill(fixture, '#input-password', 'incorrecta');
    await submit(fixture);

    http
      .expectOne('http://localhost:8000/auth/login')
      .flush({ detail: 'Credenciales inválidas' }, { status: 401, statusText: 'Unauthorized' });
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Credenciales inválidas');
    expect(navigations).toEqual([]);
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it('renders the Google entry point, with a notice only when the client id is missing', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.querySelector('app-google-sign-in')).not.toBeNull();
    if (environment.googleClientId.length === 0) {
      expect(fixture.nativeElement.textContent).toContain('googleClientId');
    }
  });

  it('keeps Google ahead of the credential fields', async () => {
    const fixture = await render();
    const google = fixture.nativeElement.querySelector('app-google-sign-in');
    const email = emailInput(fixture);

    expect(google.compareDocumentPosition(email) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('exchanges the Google credential and stores the session', async () => {
    const fixture = await render();

    fixture.componentInstance['onCredential']('google-id-token');

    const request = http.expectOne('http://localhost:8000/auth/google');
    expect(request.request.body).toEqual({ id_token: 'google-id-token' });
    request.flush(TOKEN_RESPONSE);
    await fixture.whenStable();

    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toContain('jwt-token');
    expect(navigations).toEqual(['/terreno']);
  });

  it('shows the backend error when the exchange fails', async () => {
    const fixture = await render();

    fixture.componentInstance['onCredential']('bad-token');
    http
      .expectOne('http://localhost:8000/auth/google')
      .flush({ detail: 'Token de Google inválido' }, { status: 401, statusText: 'Unauthorized' });
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('Token de Google inválido');
    expect(navigations).toEqual([]);
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });
});

function emailInput(fixture: { nativeElement: HTMLElement }): HTMLInputElement {
  return fixture.nativeElement.querySelector('#input-email') as HTMLInputElement;
}

function passwordInput(fixture: { nativeElement: HTMLElement }): HTMLInputElement {
  return fixture.nativeElement.querySelector('#input-password') as HTMLInputElement;
}

async function fill(
  fixture: { nativeElement: HTMLElement; whenStable: () => Promise<unknown> },
  selector: string,
  value: string,
): Promise<void> {
  const input = fixture.nativeElement.querySelector(selector) as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await fixture.whenStable();
}

async function submit(fixture: {
  nativeElement: HTMLElement;
  whenStable: () => Promise<unknown>;
}): Promise<void> {
  const form = fixture.nativeElement.querySelector('form');
  if (!form) throw new Error('The login form must render a <form> element.');
  form.dispatchEvent(new Event('submit', { cancelable: true }));
  await fixture.whenStable();
}
