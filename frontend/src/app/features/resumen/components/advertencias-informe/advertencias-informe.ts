import { Component, input } from '@angular/core';
import { AdvertenciaApi } from '../../../cultivos/models/cultivos.model';

/**
 * Advertencias del resultado y del diseño, arriba de todo el informe: un ajuste
 * del motor o una limitación de la corrida no puede quedar escondida al pie (S3).
 */
@Component({
  selector: 'app-advertencias-informe',
  templateUrl: './advertencias-informe.html',
})
export class AdvertenciasInforme {
  readonly advertencias = input<AdvertenciaApi[]>([]);
}
