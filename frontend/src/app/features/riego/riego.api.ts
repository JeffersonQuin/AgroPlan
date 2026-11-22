import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TerrenoRiegoApi } from './models/riego.model';

/** Lecturas del paso 3: nada más, porque el paso no escribe ni llama al agente. */
@Service()
export class RiegoApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  /** `GET /proyectos/{id}/terreno`: fuente y caudal que ya cargó el paso 1. */
  terreno(proyectoId: string): Observable<TerrenoRiegoApi> {
    return this.http.get<TerrenoRiegoApi>(`${this.baseUrl}/${proyectoId}/terreno`);
  }
}
