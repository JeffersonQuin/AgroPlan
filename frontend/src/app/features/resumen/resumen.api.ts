import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ResultadoProyectoApi } from './models/resumen.model';

/**
 * Lectura del paso 4: el documento final ya compuesto por el backend.
 *
 * El disparo, el sondeo y la aplicación de la corrida viven en `CultivosApi` desde el
 * paso 2 (`iniciarCorrida`, `obtenerCorrida`, `aplicarCorrida`): el paso 4 los reusa
 * en vez de duplicar el contrato del agente.
 */
@Service()
export class ResumenApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  /** `GET /proyectos/{id}/resultado`: 404 mientras la red no se haya generado. */
  resultado(proyectoId: string): Observable<ResultadoProyectoApi> {
    return this.http.get<ResultadoProyectoApi>(`${this.baseUrl}/${proyectoId}/resultado`);
  }
}
