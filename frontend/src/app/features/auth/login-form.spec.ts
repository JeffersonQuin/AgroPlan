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

  it('keeps the credential fields disabled while the backend has no passwords', async () => {
    const fixture = await render();

    expect(
      (fixture.nativeElement.querySelector('#input-email') as HTMLInputElement).disabled,
    ).toBe(true);
    expect(
      (fixture.nativeElement.querySelector('#input-password') as HTMLInputElement).disabled,
    ).toBe(true);
    expect(fixture.nativeElement.textContent).toContain(
      'El backend todavía no acepta correo y contraseña.',
    );
  });

  it('renders the Google entry point, with a notice only when the client id is missing', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.querySelector('app-google-sign-in')).not.toBeNull();
    if (environment.googleClientId.length === 0) {
      expect(fixture.nativeElement.textContent).toContain('googleClientId');
    }
  });

  it('has no submitable credential form left', async () => {
    const fixture = await render();

    expect(fixture.nativeElement.querySelector('form')).toBeNull();
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
