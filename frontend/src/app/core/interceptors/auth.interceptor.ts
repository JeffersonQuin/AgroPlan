import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { environment } from '../../../environments/environment';
import { AuthStore } from '../../features/auth/auth.store';

/** Attaches the bearer token to every request that targets our API. */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = inject(AuthStore).token();
  const isApiRequest = request.url.startsWith(environment.apiUrl);

  if (!token || !isApiRequest || request.headers.has('Authorization')) {
    return next(request);
  }

  return next(
    request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }),
  );
};
