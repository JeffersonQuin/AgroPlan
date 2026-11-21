import { Service, computed, inject, signal } from '@angular/core';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { AuthApi } from './auth.api';
import {
  AuthStatus,
  BackendUser,
  LOGIN_COPY,
  SESSION_STORAGE_KEY,
  TokenResponse,
} from './auth.model';

interface PersistedSession {
  token: string;
  user: BackendUser;
}

/**
 * Session state shared by the auth screens and the route guard.
 *
 * The token is kept in localStorage, so a reload keeps the session. That is the
 * trade-off the team chose: simple and survives refresh, but exposed to XSS.
 */
@Service()
export class AuthStore {
  private readonly api = inject(AuthApi);
  private readonly _status = signal<AuthStatus>('idle');
  private readonly _error = signal('');
  private readonly session = signal<PersistedSession | null>(readSession());

  readonly status = this._status.asReadonly();
  readonly error = this._error.asReadonly();

  readonly user = computed(() => this.session()?.user ?? null);
  readonly token = computed(() => this.session()?.token ?? null);
  readonly isAuthenticated = computed(() => this.session() !== null);

  readonly isSubmitting = computed(() => this._status() === 'submitting');
  readonly isSuccess = computed(() => this._status() === 'success');
  readonly copy = LOGIN_COPY;
  readonly submitLabel = computed(() => {
    const status = this._status();
    if (status === 'submitting') return this.copy.submitting;
    return this.copy.submit;
  });

  /** Exchanges the Google ID token and stores the session on success. */
  loginWithGoogle(idToken: string): Observable<boolean> {
    this._status.set('submitting');
    this._error.set('');

    return this.exchange(this.api.loginWithGoogle(idToken));
  }

  /** Creates the account on first sign-in (POST /auth/google/register). */
  registerWithGoogle(idToken: string): Observable<boolean> {
    this._status.set('submitting');
    this._error.set('');

    return this.exchange(this.api.registerWithGoogle(idToken));
  }

  private exchange(request: Observable<TokenResponse>): Observable<boolean> {
    return request.pipe(
      tap((response) => this.persist(response)),
      map(() => true),
      catchError((failure: unknown) => {
        this._status.set('error');
        this._error.set(describeError(failure));
        return of(false);
      }),
    );
  }

  logout(): void {
    this.session.set(null);
    this._status.set('idle');
    this._error.set('');
    removeSession();
  }

  private persist(response: TokenResponse): void {
    const session: PersistedSession = { token: response.access_token, user: response.usuario };
    this.session.set(session);
    this._status.set('success');
    writeSession(session);
  }
}

function describeError(failure: unknown): string {
  const detail = (failure as { error?: { detail?: unknown } })?.error?.detail;
  if (typeof detail === 'string' && detail.length > 0) return detail;
  return 'No pudimos completar el ingreso. Intentá de nuevo.';
}

function readSession(): PersistedSession | null {
  if (typeof localStorage === 'undefined') return null;

  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as PersistedSession;
    return parsed?.token && parsed?.user ? parsed : null;
  } catch {
    return null;
  }
}

function writeSession(session: PersistedSession): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

function removeSession(): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem(SESSION_STORAGE_KEY);
}
