import { HttpClient } from '@angular/common/http';
import { Service, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CrearProyectoApi,
  ProyectoApi,
  ProyectoListadoApi,
} from './models/project.model';

/**
 * HTTP contract with the FastAPI backend for projects.
 *
 * The list endpoint returns only what the card draws; every derived figure
 * (area, crop count, irrigation type) comes calculated from the backend.
 */
@Service()
export class ProjectsApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/proyectos`;

  listar(): Observable<ProyectoListadoApi[]> {
    return this.http.get<ProyectoListadoApi[]>(this.baseUrl);
  }

  crear(dto: CrearProyectoApi): Observable<ProyectoApi> {
    return this.http.post<ProyectoApi>(this.baseUrl, dto);
  }

  obtener(proyectoId: string): Observable<ProyectoApi> {
    return this.http.get<ProyectoApi>(`${this.baseUrl}/${proyectoId}`);
  }

  actualizarNombre(proyectoId: string, nombre: string, version: number): Observable<ProyectoApi> {
    return this.http.patch<ProyectoApi>(`${this.baseUrl}/${proyectoId}`, { nombre, version });
  }

  eliminar(proyectoId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${proyectoId}`);
  }
}
