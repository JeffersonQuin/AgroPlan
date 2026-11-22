import { Component } from '@angular/core';

/**
 * Banda única de modo catálogo (S3).
 *
 * Cuando la corrida se resolvió sin credenciales del modelo, el informe no tiene
 * precios, fuentes ni cifras del agente: se explica **una sola vez** y con lenguaje
 * de producto, arriba de las secciones, en vez de repetir "no informado" en cada
 * tarjeta.
 */
@Component({
  selector: 'app-modo-catalogo-informe',
  templateUrl: './modo-catalogo-informe.html',
})
export class ModoCatalogoInforme {}
