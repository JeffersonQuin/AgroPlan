import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { SESSION_STORAGE_KEY } from '../../features/auth/auth.model';
import { authInterceptor } from './auth.interceptor';

const SESSION = {
  token: 'jwt-token',
  user: {
    id: 7,
    email: 'agronomo@agroplan.com',
    nombre: null,
    foto_url: null,
    rol: 'cliente',
    activo: true,
    ultimo_acceso: null,
  },
};

function setup(withSession: boolean) {
  localStorage.clear();
  if (withSession) {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(SESSION));
  }

  const navigations: string[] = [];
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withInterceptors([authInterceptor])),
      provideHttpClientTesting(),
      {
        provide: Router,
        useValue: {
          navigate: (commands: string[]) => {
            navigations.push(commands.join('/'));
            return true;
          },
        },
      },
    ],
  });

  return {
    http: TestBed.inject(HttpTestingController),
    client: TestBed.inject(HttpClient),
    navigations,
  };
}

describe('authInterceptor', () => {
  beforeEach(() => TestBed.resetTestingModule());

  afterEach(() => localStorage.clear());

  it('adds the bearer token to requests that target the API origin', () => {
    const { http, client } = setup(true);

    client.get('http://localhost:8000/projects').subscribe({ error: () => undefined });
    const request = http.expectOne('http://localhost:8000/projects');

    expect(request.request.headers.get('Authorization')).toBe('Bearer jwt-token');
    request.flush({});
    http.verify();
  });

  it('never sends the token to a third party or a look-alike origin', () => {
    const { http, client } = setup(true);
    const urls = [
      'https://accounts.google.com/gsi/client',
      'https://evil.example/collect',
      'http://localhost:8000.evil.example/steal',
      '/relative/api',
    ];

    for (const url of urls) {
      client.get(url).subscribe({ error: () => undefined });
      const request = http.expectOne(url);
      expect(request.request.headers.has('Authorization')).toBe(false);
      request.flush({});
    }
    http.verify();
  });

  it('sends no token when there is no session', () => {
    const { http, client } = setup(false);

    client.get('http://localhost:8000/projects').subscribe({ error: () => undefined });
    const request = http.expectOne('http://localhost:8000/projects');

    expect(request.request.headers.has('Authorization')).toBe(false);
    request.flush({});
    http.verify();
  });

  it('clears the session and redirects to /login on a 401 from the API', () => {
    const { http, client, navigations } = setup(true);

    client.get('http://localhost:8000/projects').subscribe({ error: () => undefined });
    http
      .expectOne('http://localhost:8000/projects')
      .flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });

    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
    expect(navigations).toContain('/login');
    http.verify();
  });
});
