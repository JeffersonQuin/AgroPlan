import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TokenResponse } from './auth.model';

/** HTTP contract with the FastAPI backend for authentication. */
@Service()
export class AuthApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/auth`;

  /** Exchanges a Google ID token for a backend access token. */
  loginWithGoogle(idToken: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/google`, { id_token: idToken });
  }

  /** Creates the account on first sign-in. */
  registerWithGoogle(idToken: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/google/register`, {
      id_token: idToken,
    });
  }
}
