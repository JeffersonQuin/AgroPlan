import { HttpErrorResponse } from '@angular/common/http';
import { Service, computed, inject, signal } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { mensajeDeError } from '../../projects/state/projects.store';
import { ProjectsApi } from '../../projects/projects.api';
import { CultivosApi } from '../cultivos.api';
import {
  BalanceApi,
  BloqueApi,
  CrearBloqueApi,
  CultivoCatalogoApi,
  CultivoRespuestaApi,
  EditarBloqueApi,
  ProductoElegido,
} from '../models/cultivos.model';

export type EstadoPaso2 =
  | 'inicial'
  | 'cargando'
  | 'listo'
  | 'guardando'
  | 'generando'
  | 'error';

/**
 * Step 2 state, backed by the API.
 *
 * The backend owns every figure: area, percentage, block demand, Kc, soil verdict
 * and the balance panel. The store only keeps the collection, the catalogue and
 * the selection, and refreshes the panel after each write.
 */
@Service()
export class CultivosStore {
  private readonly api = inject(CultivosApi);
  private readonly projectsApi = inject(ProjectsApi);

  private readonly _proyectoId = signal<string | null>(null);
  private readonly _nombreProyecto = signal('');
  private readonly _areaM2 = signal(0);
  private readonly _caudalM3h = signal(0);
  private readonly _sueloCodigo = signal('');
  private readonly _bloques = signal<BloqueApi[]>([]);
  private readonly _balance = signal<BalanceApi | null>(null);
  private readonly _catalogo = signal<CultivoCatalogoApi[]>([]);
  private readonly _estado = signal<EstadoPaso2>('inicial');
  private readonly _error = signal<string | null>(null);
  private readonly _seleccionado = signal<string | null>(null);
  private readonly _productos = signal<ProductoElegido[]>([]);
  private readonly _siembra = signal(hoy());
  private readonly _verticesTerreno = signal<{ x: number; y: number }[]>([]);
  private readonly _generado = signal(false);
  private sondeo: ReturnType<typeof setInterval> | null = null;

  readonly nombreProyecto = this._nombreProyecto.asReadonly();
  readonly areaM2 = this._areaM2.asReadonly();
  readonly caudalM3h = this._caudalM3h.asReadonly();
  readonly sueloCodigo = this._sueloCodigo.asReadonly();
  readonly bloques = this._bloques.asReadonly();
  readonly balance = this._balance.asReadonly();
  readonly catalogo = this._catalogo.asReadonly();
  readonly estado = this._estado.asReadonly();
  readonly error = this._error.asReadonly();
  readonly seleccionado = this._seleccionado.asReadonly();
  readonly productos = this._productos.asReadonly();
  readonly siembra = this._siembra.asReadonly();
  readonly verticesTerreno = this._verticesTerreno.asReadonly();
  /** ``true`` cuando ya hay una distribución generada por el agente. */
  readonly generado = this._generado.asReadonly();

  readonly cargando = computed(() => this._estado() === 'cargando');
  readonly guardando = computed(() => this._estado() === 'guardando');
  readonly generando = computed(() => this._estado() === 'generando');
  readonly puedeGenerar = computed(
    () => this._productos().length > 0 && !this.generando() && !this.generado(),
  );

  readonly estadoGuardadoLabel = computed(() => {
    switch (this._estado()) {
      case 'cargando':
        return 'Cargando…';
      case 'guardando':
        return 'Guardando…';
      case 'listo':
        return 'Guardado';
      case 'error':
        return 'No se pudo guardar';
      default:
        return 'Sin guardar';
    }
  });

  readonly cultivosCount = computed(() => this._bloques().length);
  readonly asignadoPct = computed(() => {
    const balance = this._balance();
    if (balance === null || balance.terreno_m2 <= 0) return 0;
    return Math.round((balance.asignado_m2 / balance.terreno_m2) * 1000) / 10;
  });
  readonly estadoBalance = computed(() => this._balance()?.estado ?? 'ajustado');
  readonly alertas = computed(() => this._balance()?.alertas ?? []);

  /** Opciones del selector de especie: el catálogo activo del backend. */
  readonly opcionesCultivo = computed(() =>
    this._catalogo().map((cultivo) => ({
      value: cultivo.codigo,
      label: cultivo.nombre,
      demanda: cultivo.demanda_agua_l_m2_dia,
      ciclo: cultivo.ciclo_dias,
      kc: cultivo.kc,
      color: cultivo.color,
    })),
  );

  readonly cultivoSeleccionado = computed(() => {
    const codigo = this._seleccionado() ?? this._bloques()[0]?.cultivo_codigo ?? null;
    if (codigo === null) return null;
    return this.opcionesCultivo().find((opcion) => opcion.value === codigo) ?? null;
  });

  cargar(proyectoId: string): void {
    this._proyectoId.set(proyectoId);
    this._estado.set('cargando');
    this._error.set(null);

    forkJoin({
      proyecto: this.projectsApi.obtener(proyectoId),
      terreno: this.api.terreno(proyectoId).pipe(catchError(() => of(null))),
      bloques: this.api.listar(proyectoId).pipe(catchError(() => of([] as BloqueApi[]))),
      balance: this.api.balance(proyectoId).pipe(catchError(() => of(null))),
      catalogo: this.api.catalogo().pipe(catchError(() => of([] as CultivoCatalogoApi[]))),
    }).subscribe({
      next: ({ proyecto, terreno, bloques, balance, catalogo }) => {
        this._nombreProyecto.set(proyecto.nombre);
        this._areaM2.set(terreno?.area_m2 ?? 0);
        this._caudalM3h.set(terreno?.caudal_efectivo_m3h ?? 0);
        this._sueloCodigo.set(terreno?.suelo_codigo ?? '');
        this._verticesTerreno.set(terreno?.geometria?.vertices ?? []);
        this._bloques.set(bloques);
        this._generado.set(bloques.length > 0);
        this._balance.set(balance);
        this._catalogo.set(catalogo.filter((cultivo) => cultivo.activo));
        this._estado.set('listo');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }

  /** Agrega un cultivo por porcentaje del terreno; el backend reparte la geometría. */
  agregar(cultivoCodigo: string, porcentaje: number, etiqueta: string | null = null) {
    const proyectoId = this._proyectoId();
    if (proyectoId === null) return null;

    const dto: CrearBloqueApi = {
      cultivo_codigo: cultivoCodigo,
      etiqueta: etiqueta ?? `${this.cultivosCount() + 1}`,
      modo: 'porcentaje',
      porcentaje,
    };
    return this.escribir(this.api.crear(proyectoId, dto));
  }

  editar(bloqueId: string, dto: EditarBloqueApi) {
    const proyectoId = this._proyectoId();
    if (proyectoId === null) return null;
    return this.escribir(this.api.editar(proyectoId, bloqueId, dto));
  }

  eliminar(bloqueId: string) {
    const proyectoId = this._proyectoId();
    if (proyectoId === null) return null;

    this._estado.set('guardando');
    this._error.set(null);
    return this.api.eliminar(proyectoId, bloqueId).pipe(
      tap({
        next: () => {
          this._bloques.update((bloques) => bloques.filter((bloque) => bloque.id !== bloqueId));
          this.refrescarBalance();
        },
        error: (error: HttpErrorResponse) => {
          this._error.set(mensajeDeError(error));
          this._estado.set('error');
        },
      }),
    );
  }

  seleccionar(codigo: string): void {
    this._seleccionado.set(codigo);
  }

  // ------------------------------------------------------------------- //
  // Lista de productos y generación con el agente
  // ------------------------------------------------------------------- //

  /** Agrega un producto del catálogo, o uno nuevo escrito a mano. */
  agregarProducto(codigo: string | null, texto: string): void {
    const limpio = texto.trim();
    if (codigo === null && limpio.length < 2) return;

    const catalogo = codigo === null ? undefined : this.catalogoPorCodigo(codigo);
    const etiqueta = catalogo?.nombre ?? limpio;
    if (this._productos().some((producto) => producto.etiqueta === etiqueta)) return;

    this._productos.update((productos) => [
      ...productos,
      {
        codigo,
        texto: limpio,
        etiqueta,
        color: catalogo?.color ?? '#4CAF50',
      },
    ]);
  }

  quitarProducto(indice: number): void {
    this._productos.update((productos) =>
      productos.filter((_, posicion) => posicion !== indice),
    );
  }

  setSiembra(fecha: string): void {
    this._siembra.set(fecha || hoy());
  }

  /**
   * Manda la lista al agente, espera el resultado y aplica la distribución.
   *
   * El agente decide **cuánta área** va a cada producto; el motor geométrico arma las
   * parcelas al aplicar. Sólo se puede generar una vez: para repetirlo el usuario
   * necesita el plan premium (lo gatea la pantalla).
   */
  generar(): void {
    const proyectoId = this._proyectoId();
    if (proyectoId === null || !this.puedeGenerar()) return;

    this._estado.set('generando');
    this._error.set(null);

    this.api
      .iniciarCorrida(proyectoId, {
        productos: this._productos().map((producto) =>
          producto.codigo !== null
            ? { cultivo_codigo: producto.codigo }
            : { producto_texto: producto.texto },
        ),
        siembra: this._siembra() || null,
      })
      .subscribe({
        next: (inicio) => this.sondear(proyectoId, inicio.corrida_id),
        error: (error: HttpErrorResponse) => {
          this._error.set(mensajeDeError(error));
          this._estado.set('error');
        },
      });
  }

  /** Consulta la corrida hasta que termina, y aplica la propuesta si salió bien. */
  private sondear(proyectoId: string, corridaId: string): void {
    this.detenerSondeo();
    this.sondeo = setInterval(() => {
      this.api.obtenerCorrida(proyectoId, corridaId).subscribe({
        next: (detalle) => {
          if (detalle.estado === 'ok') {
            this.detenerSondeo();
            this.aplicar(proyectoId, corridaId);
          }
          if (detalle.estado === 'error') {
            this.detenerSondeo();
            this._error.set(detalle.error_detalle ?? 'El agente no pudo generar la propuesta');
            this._estado.set('error');
          }
        },
        error: (error: HttpErrorResponse) => {
          this.detenerSondeo();
          this._error.set(mensajeDeError(error));
          this._estado.set('error');
        },
      });
    }, 1500);
  }

  private detenerSondeo(): void {
    if (this.sondeo !== null) {
      clearInterval(this.sondeo);
      this.sondeo = null;
    }
  }

  private aplicar(proyectoId: string, corridaId: string): void {
    this.api.aplicarCorrida(proyectoId, corridaId).subscribe({
      next: () => {
        this._generado.set(true);
        this._productos.set([]);
        this.recargarBloques(proyectoId);
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }

  private recargarBloques(proyectoId: string): void {
    forkJoin({
      bloques: this.api.listar(proyectoId),
      balance: this.api.balance(proyectoId),
    }).subscribe({
      next: ({ bloques, balance }) => {
        this._bloques.set(bloques);
        this._balance.set(balance);
        this._estado.set('listo');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }

  private catalogoPorCodigo(codigo: string): CultivoCatalogoApi | undefined {
    return this._catalogo().find((cultivo) => cultivo.codigo === codigo);
  }

  /** Recarga sólo el panel: tras un borrado el backend no devuelve el balance. */
  private refrescarBalance(): void {
    const proyectoId = this._proyectoId();
    if (proyectoId === null) return;
    this.api.balance(proyectoId).subscribe({
      next: (balance) => {
        this._balance.set(balance);
        this._estado.set('listo');
      },
      error: (error: HttpErrorResponse) => {
        this._error.set(mensajeDeError(error));
        this._estado.set('error');
      },
    });
  }

  private escribir(peticion: ReturnType<CultivosApi['crear']>) {
    this._estado.set('guardando');
    this._error.set(null);
    return peticion.pipe(
      tap({
        next: (respuesta: CultivoRespuestaApi) => {
          this._bloques.update((bloques) => {
            const sinViejo = bloques.filter((bloque) => bloque.id !== respuesta.bloque.id);
            return [...sinViejo, respuesta.bloque].sort((a, b) => a.orden - b.orden);
          });
          this._balance.set(respuesta.balance);
          this._estado.set('listo');
        },
        error: (error: HttpErrorResponse) => {
          this._error.set(mensajeDeError(error));
          this._estado.set('error');
        },
      }),
    );
  }
}

/** Hoy en formato `YYYY-MM-DD`, que es lo que espera el backend. */
function hoy(): string {
  const ahora = new Date();
  const mes = `${ahora.getMonth() + 1}`.padStart(2, '0');
  const dia = `${ahora.getDate()}`.padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}
