import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  BalanceApi,
  BloqueApi,
  CrearBloqueApi,
  CultivoCatalogoApi,
  CultivoRespuestaApi,
  EditarBloqueApi,
  ResumenTerrenoApi,
} from './models/cultivos.model';

/** HTTP contract with the FastAPI backend for step 2. */
@Service()
export class CultivosApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  catalogo(): Observable<CultivoCatalogoApi[]> {
    return this.http.get<CultivoCatalogoApi[]>(`${environment.apiUrl}/catalogos/cultivos`);
  }

  terreno(proyectoId: string): Observable<ResumenTerrenoApi> {
    return this.http.get<ResumenTerrenoApi>(`${this.baseUrl}/${proyectoId}/terreno`);
  }

  listar(proyectoId: string): Observable<BloqueApi[]> {
    return this.http.get<BloqueApi[]>(`${this.baseUrl}/${proyectoId}/cultivos`);
  }

  balance(proyectoId: string): Observable<BalanceApi> {
    return this.http.get<BalanceApi>(`${this.baseUrl}/${proyectoId}/cultivos/balance`);
  }

  crear(proyectoId: string, dto: CrearBloqueApi): Observable<CultivoRespuestaApi> {
    return this.http.post<CultivoRespuestaApi>(`${this.baseUrl}/${proyectoId}/cultivos`, dto);
  }

  editar(
    proyectoId: string,
    bloqueId: string,
    dto: EditarBloqueApi,
  ): Observable<CultivoRespuestaApi> {
    return this.http.patch<CultivoRespuestaApi>(
      `${this.baseUrl}/${proyectoId}/cultivos/${bloqueId}`,
      dto,
    );
  }

  eliminar(proyectoId: string, bloqueId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${proyectoId}/cultivos/${bloqueId}`);
  }
}
