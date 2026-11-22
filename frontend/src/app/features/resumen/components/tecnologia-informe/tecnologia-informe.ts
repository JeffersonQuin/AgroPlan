import { Component, input } from '@angular/core';
import { formatearNumero, textoEmisor, textoSistema } from '../../formato-informe';
import { SistemaInformeApi } from '../../models/resumen.model';

/** Tecnología y cabezal: el sistema que eligió el motor, con su eficiencia (S1, S9). */
@Component({
  selector: 'app-tecnologia-informe',
  templateUrl: './tecnologia-informe.html',
})
export class TecnologiaInforme {
  readonly sistema = input<SistemaInformeApi | null>(null);
  readonly eficiencia = input<number | null>(null);

  protected readonly formatearNumero = formatearNumero;
  protected readonly textoEmisor = textoEmisor;
  protected readonly textoSistema = textoSistema;
}
