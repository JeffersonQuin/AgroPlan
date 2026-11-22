import { HttpErrorResponse } from '@angular/common/http';
import { InjectionToken, Service, computed, inject, signal } from '@angular/core';
import { Subscription, forkJoin, of, throwError, timer } from 'rxjs';
import { catchError, exhaustMap, takeWhile } from 'rxjs/operators';
import { CultivosApi } from '../../cultivos/cultivos.api';
import {
  AdvertenciaApi,
  CultivoCatalogoApi,
  CorridaDetalleApi,
  ResumenTerrenoApi,
} from '../../cultivos/models/cultivos.model';
import { ProjectsApi } from '../../projects/projects.api';
import { EstadoProyectoApi } from '../../projects/models/project.model';
import { mensajeDeError } from '../../projects/state/projects.store';
import { SueloApi, WATER_SOURCE_OPTIONS } from '../../terrain/models/terrain.model';
import { TerrainApi } from '../../terrain/terrain.api';
import { ENERGIA_OPTIONS, PRESUPUESTO_MINIMO_BS } from '../../wizard/models/restricciones.model';
import { WizardDraftStore } from '../../wizard/state/wizard-draft.store';
import { ResumenApi } from '../resumen.api';
import { descargarBlob, nombreDeArchivo } from '../descarga-pdf';
import {
  ProductoResumen,
  RestriccionesResumen,
  ResultadoProyectoApi,
  TerrenoResumen,
} from '../models/resumen.model';

/**
 * Estados del flujo del paso 4 (S2).
 *
 * El orden importa: el informe se genera **una sola vez**, así que un proyecto con
 * resultado salta directo a `informe` y nunca vuelve a `listo-para-generar`.
 */
export type EstadoResumen =
  'cargando' | 'sin-borrador' | 'listo-para-generar' | 'generando' | 'error' | 'informe';

/** Estados terminales de una corrida; el resto sigue sondeando. */
const CORRIDA_TERMINAL: readonly string[] = ['ok', 'error', 'descartada'];

/**
 * Cada cuánto se consulta la corrida mientras el agente trabaja.
 *
 * Es un token para que los tests no esperen dos segundos reales por cada sondeo; en
 * producción vale 2 s (S2: el botón dispara, el usuario ve el progreso).
 */
export const RESUMEN_POLL_MS = new InjectionToken<number>('RESUMEN_POLL_MS', {
  factory: () => 2000,
});

const ESTADO_PROYECTO_LABEL: Record<EstadoProyectoApi, string> = {
  borrador: 'Borrador',
  en_progreso: 'En progreso',
  completado: 'Cómputo listo',
};

/**
 * Paso 4: el informe final.
 *
 * Máquina de estados:
 *
 * - `cargando`: se leen proyecto, terreno, catálogos y el resultado que ya exista.
 * - `sin-borrador`: el borrador del paso 2 está vacío; se explica qué falta.
 * - `listo-para-generar`: el modal muestra el resumen previo y espera confirmación.
 * - `generando`: la corrida se disparó y se sondea hasta que termina.
 * - `error`: el backend falló; el mensaje y el reintento viven acá.
 * - `informe`: hay resultado y las secciones del informe lo consumen.
 *
 * Nada se dispara hasta que el usuario confirma el modal, y un proyecto con resultado
 * no vuelve a llamar al agente: regenerar es plan premium.
 */
@Service()
export class ResumenStore {
  private readonly api = inject(ResumenApi);
  private readonly cultivosApi = inject(CultivosApi);
  private readonly projectsApi = inject(ProjectsApi);
  private readonly terrainApi = inject(TerrainApi);
  private readonly borrador = inject(WizardDraftStore);
  private readonly pollMs = inject(RESUMEN_POLL_MS);

  private readonly _proyectoId = signal('');
  private readonly _nombreProyecto = signal('');
  private readonly _estado = signal<EstadoResumen>('cargando');
  private readonly _modalAbierto = signal(false);
  private readonly _terreno = signal<TerrenoResumen | null>(null);
  private readonly _catalogo = signal<CultivoCatalogoApi[]>([]);
  private readonly _resultado = signal<ResultadoProyectoApi | null>(null);
  private readonly _error = signal<string | null>(null);
  private readonly _corridaId = signal<string | null>(null);
  private readonly _estadoCorrida = signal<string | null>(null);
  private readonly _descargandoPdf = signal(false);
  private readonly _errorPdf = signal<string | null>(null);

  private sondeo: Subscription | null = null;

  readonly estado = this._estado.asReadonly();
  readonly modalAbierto = this._modalAbierto.asReadonly();
  readonly terreno = this._terreno.asReadonly();
  readonly resultado = this._resultado.asReadonly();
  readonly error = this._error.asReadonly();
  readonly corridaId = this._corridaId.asReadonly();
  readonly estadoCorrida = this._estadoCorrida.asReadonly();
  readonly descargandoPdf = this._descargandoPdf.asReadonly();
  readonly errorPdf = this._errorPdf.asReadonly();

  readonly nombreProyecto = computed(() => {
    const terreno = this._terreno();
    return this._nombreProyecto() || terreno?.nombre || 'Proyecto';
  });

  readonly estadoProyectoLabel = computed(() => {
    const resultado = this._resultado();
    return resultado === null ? '' : ESTADO_PROYECTO_LABEL[resultado.estado];
  });

  /** Un proyecto con informe no se regenera (S2). */
  readonly tieneInforme = computed(() => this._resultado() !== null);

  /** Avisos del motor y del agente que acompañan al informe (S3). */
  readonly advertencias = computed<AdvertenciaApi[]>(() => this._resultado()?.advertencias ?? []);

  /** El borrador del paso 2 está vacío: el modal no deja generar. */
  readonly sinBorrador = computed(() => this.borrador.vacio());

  /** Productos del borrador con la imagen de su ficha curada, si la tiene (S4). */
  readonly productos = computed<ProductoResumen[]>(() => {
    const catalogo = this._catalogo();
    return this.borrador.productos().map((producto) => {
      const ficha =
        producto.codigo === null
          ? undefined
          : catalogo.find((cultivo) => cultivo.codigo === producto.codigo);
      return {
        etiqueta: producto.etiqueta,
        inicial: producto.etiqueta.charAt(0).toUpperCase(),
        color: producto.color,
        imagenUrl: ficha?.imagen_url ?? null,
        imagenCredito: ficha?.imagen_credito ?? null,
      };
    });
  });

  readonly siembra = computed(() => this.borrador.siembra());

  readonly restricciones = computed<RestriccionesResumen>(() => ({
    energiaLabel:
      ENERGIA_OPTIONS.find((opcion) => opcion.value === this.borrador.energia())?.label ?? '',
    tanqueL: this.borrador.tanqueL(),
    presupuestoBs: this.borrador.presupuestoEfectivo(),
    presupuestoBajoElPiso: this.borrador.presupuestoBajoElPiso(),
    presupuestoMinimoBs: PRESUPUESTO_MINIMO_BS,
  }));

  /**
   * Carga el paso: proyecto, terreno, catálogos y el resultado existente.
   *
   * El borrador (`WizardDraftStore`) tiene que estar cargado antes: la página lo hace
   * en su constructor, porque de él depende si el flujo arranca en `sin-borrador`.
   */
  cargar(proyectoId: string): void {
    this._proyectoId.set(proyectoId);
    this._estado.set('cargando');
    this._error.set(null);

    forkJoin({
      proyecto: this.projectsApi.obtener(proyectoId),
      terreno: this.cultivosApi.terreno(proyectoId).pipe(catchError(() => of(null))),
      suelos: this.terrainApi.suelos().pipe(catchError(() => of([] as SueloApi[]))),
      catalogo: this.cultivosApi.catalogo().pipe(catchError(() => of([] as CultivoCatalogoApi[]))),
      // 404 es el caso normal: la red todavía no se generó, así que no hay informe.
      resultado: this.api
        .resultado(proyectoId)
        .pipe(
          catchError((error: HttpErrorResponse) =>
            error.status === 404 ? of(null) : throwError(() => error),
          ),
        ),
    }).subscribe({
      next: ({ proyecto, terreno, suelos, catalogo, resultado }) => {
        this._nombreProyecto.set(proyecto.nombre);
        this._catalogo.set(catalogo);
        this._terreno.set(
          terreno === null
            ? null
            : {
                nombre: terreno.nombre_parcela,
                areaM2: terreno.area_m2,
                sueloCodigo: terreno.suelo_codigo,
                sueloNombre: nombreDeSuelo(suelos, terreno.suelo_codigo),
                fuenteLabel:
                  WATER_SOURCE_OPTIONS.find((opcion) => opcion.value === terreno.fuente_agua)
                    ?.label ?? '',
                caudalM3h: terreno.caudal_efectivo_m3h,
                pendientePct: terreno.pendiente_pct,
              },
        );

        if (resultado !== null) {
          this.mostrarInforme(resultado);
          return;
        }
        if (this.borrador.vacio()) {
          this._estado.set('sin-borrador');
          return;
        }
        this._estado.set('listo-para-generar');
        this._modalAbierto.set(true);
      },
      error: (error: HttpErrorResponse) => this.fallar(error),
    });
  }

  abrirModal(): void {
    if (this._resultado() !== null || this._estado() === 'generando') return;
    this._modalAbierto.set(true);
  }

  cerrarModal(): void {
    this._modalAbierto.set(false);
  }

  /**
   * Confirma el modal y dispara la corrida con el borrador completo (S2).
   *
   * Se manda **una sola vez**: si ya hay informe o ya hay una corrida en curso, no
   * vuelve a gastar tokens.
   */
  generar(): void {
    const proyectoId = this._proyectoId();
    if (proyectoId === '') return;
    if (this._estado() === 'generando' || this._resultado() !== null) return;
    if (this.borrador.vacio()) return;

    const { productos, siembra, restricciones } = this.borrador.aPayload();

    this._modalAbierto.set(false);
    this._error.set(null);
    this._estado.set('generando');
    this._estadoCorrida.set(null);
    this._corridaId.set(null);

    this.cultivosApi.iniciarCorrida(proyectoId, { productos, siembra, restricciones }).subscribe({
      next: (inicio) => {
        this._corridaId.set(inicio.corrida_id);
        this._estadoCorrida.set(inicio.estado);
        this.sondear(proyectoId, inicio.corrida_id);
      },
      error: (error: HttpErrorResponse) => this.fallar(error),
    });
  }

  /**
   * Descarga el informe en PDF del proyecto actual (S8).
   *
   * El backend arma el documento; acá sólo se baja el `Blob`. Un fallo se muestra
   * junto al botón y no cambia el estado del informe: la pantalla sigue igual.
   */
  descargarPdf(): void {
    const proyectoId = this._proyectoId();
    if (proyectoId === '' || this._descargandoPdf()) return;

    this._descargandoPdf.set(true);
    this._errorPdf.set(null);
    this.api.pdf(proyectoId).subscribe({
      next: (respuesta) => {
        const blob = respuesta.body;
        if (blob === null) {
          this._errorPdf.set('El backend no devolvió el informe en PDF.');
        } else {
          descargarBlob(blob, nombreDeArchivo(respuesta, proyectoId));
        }
        this._descargandoPdf.set(false);
      },
      error: () => {
        this._errorPdf.set('No se pudo descargar el informe. Reintentá en unos segundos.');
        this._descargandoPdf.set(false);
      },
    });
  }

  /** Botón de reintento del estado `error`: vuelve a disparar con el mismo borrador. */
  reintentar(): void {
    this.generar();
  }

  /** Cancela el sondeo: lo llama la página al destruirse. */
  detenerSondeo(): void {
    this.sondeo?.unsubscribe();
    this.sondeo = null;
  }

  /**
   * Sondea la corrida hasta un estado terminal (S2).
   *
   * `timer(0, pollMs)` consulta enseguida y después cada 2 s; `exhaustMap` evita
   * encimar consultas si una tarda más que el intervalo, y `takeWhile` con
   * `inclusive` corta el sondeo justo cuando llega el estado final.
   */
  private sondear(proyectoId: string, corridaId: string): void {
    this.detenerSondeo();

    this.sondeo = timer(0, this.pollMs)
      .pipe(
        exhaustMap(() => this.cultivosApi.obtenerCorrida(proyectoId, corridaId)),
        takeWhile((detalle) => !CORRIDA_TERMINAL.includes(detalle.estado), true),
      )
      .subscribe({
        next: (detalle) => this.alTerminarCorrida(detalle, proyectoId, corridaId),
        error: (error: HttpErrorResponse) => this.fallar(error),
      });
  }

  private alTerminarCorrida(
    detalle: CorridaDetalleApi,
    proyectoId: string,
    corridaId: string,
  ): void {
    this._estadoCorrida.set(detalle.estado);
    if (!CORRIDA_TERMINAL.includes(detalle.estado)) return;

    if (detalle.estado !== 'ok') {
      this._error.set(
        detalle.error_detalle ?? 'El agente no pudo generar el informe. Probá de nuevo.',
      );
      this._estado.set('error');
      return;
    }
    this.aplicar(proyectoId, corridaId);
  }

  /** Materializa la propuesta congelada: el único paso que escribe el proyecto. */
  private aplicar(proyectoId: string, corridaId: string): void {
    this.cultivosApi.aplicarCorrida(proyectoId, corridaId).subscribe({
      // `aplicarCorrida` devuelve `unknown` porque el paso 2 no conoce este contrato:
      // el backend responde `ResultadoProyectoOut`, que es el modelo del paso 4.
      next: (respuesta) => this.mostrarInforme(respuesta as ResultadoProyectoApi),
      error: (error: HttpErrorResponse) => {
        // 409 = corrida ya aplicada (por ejemplo, otra pestaña): el informe existe.
        if (error.status === 409) {
          this.recargarResultado(proyectoId);
          return;
        }
        this.fallar(error);
      },
    });
  }

  private recargarResultado(proyectoId: string): void {
    this.api.resultado(proyectoId).subscribe({
      next: (resultado) => this.mostrarInforme(resultado),
      error: (error: HttpErrorResponse) => this.fallar(error),
    });
  }

  private mostrarInforme(resultado: ResultadoProyectoApi): void {
    this.detenerSondeo();
    this._resultado.set(resultado);
    this._modalAbierto.set(false);
    this._error.set(null);
    this._estadoCorrida.set(null);
    this._corridaId.set(null);
    this._estado.set('informe');
  }

  private fallar(error: HttpErrorResponse): void {
    this.detenerSondeo();
    this._error.set(mensajeDeError(error));
    this._estado.set('error');
  }
}

/** Nombre del suelo del catálogo; si no vino, el código se vuelve legible. */
function nombreDeSuelo(suelos: SueloApi[], codigo: string): string {
  const suelo = suelos.find((opcion) => opcion.codigo === codigo);
  if (suelo !== undefined) return suelo.nombre;
  const legible = codigo.replace(/_/g, ' ').trim();
  return legible === '' ? '' : legible.charAt(0).toUpperCase() + legible.slice(1);
}
