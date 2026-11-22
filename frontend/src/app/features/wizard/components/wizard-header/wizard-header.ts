import { Component, DestroyRef, computed, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { matCheckOutline } from '@ng-icons/material-symbols/outline';
import { ResumenApi } from '../../../resumen/resumen.api';
import { descargarBlob, nombreDeArchivo } from '../../../resumen/descarga-pdf';

interface PasoWizard {
  numero: number;
  nombre: string;
}

const PASOS: readonly PasoWizard[] = [
  { numero: 1, nombre: 'Terreno' },
  { numero: 2, nombre: 'Cultivos' },
  { numero: 3, nombre: 'Sistema' },
  { numero: 4, nombre: 'Resultado' },
];

/**
 * Wizard chrome shared by the four steps: brand, project name, the stepper and the
 * save state. Each page hands it the current step and its own state, so the header
 * never reaches into another feature's store.
 */
@Component({
  selector: 'app-wizard-header',
  imports: [NgIcon],
  viewProviders: [provideIcons({ matCheckOutline })],
  templateUrl: './wizard-header.html',
})
export class WizardHeader {
  private readonly api = inject(ResumenApi);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly paso = input<number>(1);
  readonly nombreProyecto = input<string>('Proyecto');
  readonly estadoGuardado = input<string>('Sin guardar');
  readonly guardar = output<void>();

  protected readonly pasos = PASOS;
  protected readonly actual = computed(() => this.paso());
  protected readonly exportando = signal(false);
  protected readonly errorExportacion = signal<string | null>(null);

  /**
   * Descarga el informe del proyecto actual desde el header (S8).
   *
   * El id sale de la ruta del wizard; el PDF lo genera el backend. Si falla, el
   * error se muestra en el header y el resto de la pantalla sigue funcionando.
   */
  exportarPdf(): void {
    const proyectoId = this.proyectoId();
    if (proyectoId === '' || this.exportando()) return;

    this.exportando.set(true);
    this.errorExportacion.set(null);
    this.api
      .pdf(proyectoId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (respuesta) => {
          const blob = respuesta.body;
          if (blob === null) {
            this.errorExportacion.set('El informe en PDF todavía no está disponible.');
          } else {
            descargarBlob(blob, nombreDeArchivo(respuesta, proyectoId));
          }
          this.exportando.set(false);
        },
        error: () => {
          this.errorExportacion.set('No se pudo exportar el PDF.');
          this.exportando.set(false);
        },
      });
  }

  private proyectoId(): string {
    const deLaRuta = this.route.snapshot.paramMap.get('proyectoId');
    if (deLaRuta !== null && deLaRuta !== '') return deLaRuta;
    const coincidencia = /proyectos\/([^/]+)/.exec(this.router.url);
    return coincidencia?.[1] ?? '';
  }

  protected estadoPaso(numero: number): 'hecho' | 'activo' | 'pendiente' {
    if (numero < this.actual()) return 'hecho';
    return numero === this.actual() ? 'activo' : 'pendiente';
  }
}
