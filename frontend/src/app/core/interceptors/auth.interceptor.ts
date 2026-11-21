import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthStore } from '../../features/auth/auth.store';

/**
 * Attaches the bearer token to requests that target our API and clears the
 * session when the backend rejects it (expired or revoked token).
 *
 * The comparison is by origin, not by prefix: a prefix check would leak the
 * header to `http://localhost:8000.evil.example`.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthStore);
  const router = inject(Router);

  const targetsApi = isApiOrigin(request.url);

  if (!targetsApi) return next(request);

  const token = auth.token();
  const outgoing =
    token && !request.headers.has('Authorization')
      ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : request;

  return next(outgoing).pipe(
    catchError((failure: unknown) => {
      if (failure instanceof HttpErrorResponse && failure.status === 401) {
        auth.logout();
        void router.navigate(['/login']);
      }
      return throwError(() => failure);
    }),
  );
};

function isApiOrigin(url: string): boolean {
  try {
    const apiOrigin = new URL(environment.apiUrl).origin;
    const base = typeof location === 'undefined' ? apiOrigin : location.origin;
    return new URL(url, base).origin === apiOrigin;
  } catch {
    return false;
  }
}
