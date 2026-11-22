import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { GuardarTerrenoApi, SueloApi, TerrenoApi } from './models/terrain.model';

/**
 * HTTP contract with the FastAPI backend for step 1.
 *
 * `PUT` creates the terrain (the backend answers 409 if it already exists) and
 * `PATCH` updates it, so the wizard stays usable after re-entering the step.
 */
@Service()
export class TerrainApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  suelos(): Observable<SueloApi[]> {
    return this.http.get<SueloApi[]>(`${environment.apiUrl}/catalogos/suelos`);
  }

  obtener(proyectoId: string): Observable<TerrenoApi> {
    return this.http.get<TerrenoApi>(`${this.baseUrl}/${proyectoId}/terreno`);
  }

  guardar(
    proyectoId: string,
    payload: GuardarTerrenoApi,
    existe: boolean,
  ): Observable<TerrenoApi> {
    const url = `${this.baseUrl}/${proyectoId}/terreno`;
    return existe
      ? this.http.patch<TerrenoApi>(url, payload)
      : this.http.put<TerrenoApi>(url, payload);
  }
}
