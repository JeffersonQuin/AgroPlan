import { Service, computed, signal } from '@angular/core';

/** Un producto que el usuario quiere sembrar, mientras arma el proyecto. */
export interface ProductoBorrador {
  /** Código del catálogo, o ``null`` si es un producto nuevo escrito a mano. */
  codigo: string | null;
  /** Lo que se manda al agente cuando no hay código. */
  texto: string;
  etiqueta: string;
  color: string;
}

const CLAVE = 'agroplan.borrador';

interface Borrador {
  proyectoId: string;
  productos: ProductoBorrador[];
  siembra: string;
}

/**
 * Borrador del wizard: lo que el usuario elige en los pasos 1 a 3.
 *
 * Los pasos no llaman al agente ni escriben en el proyecto: sólo leen datos y guardan
 * acá lo que el usuario elige. El agente corre **una vez**, al generar el resumen del
 * paso 4, y ahí se manda todo junto. Eso mantiene el costo en un solo prompt.
 *
 * Se guarda en `localStorage` por proyecto para que recargar no borre el trabajo.
 */
@Service()
export class WizardDraftStore {
  private readonly _productos = signal<ProductoBorrador[]>([]);
  private readonly _siembra = signal(hoy());
  private readonly _proyectoId = signal('');

  readonly productos = this._productos.asReadonly();
  readonly siembra = this._siembra.asReadonly();

  readonly cantidad = computed(() => this._productos().length);
  readonly vacio = computed(() => this._productos().length === 0);

  /** Carga el borrador del proyecto, si había uno guardado. */
  cargar(proyectoId: string): void {
    this._proyectoId.set(proyectoId);
    const guardado = leer(proyectoId);
    if (guardado === null) {
      this._productos.set([]);
      this._siembra.set(hoy());
      return;
    }
    this._productos.set(guardado.productos);
    this._siembra.set(guardado.siembra);
  }

  agregarProducto(
    codigo: string | null,
    texto: string,
    etiqueta: string,
    color: string,
  ): void {
    const limpio = texto.trim();
    if (codigo === null && limpio.length < 2) return;
    if (this._productos().some((producto) => producto.etiqueta === etiqueta)) return;

    this._productos.update((productos) => [
      ...productos,
      { codigo, texto: limpio, etiqueta, color },
    ]);
    this.guardar();
  }

  quitarProducto(indice: number): void {
    this._productos.update((productos) =>
      productos.filter((_, posicion) => posicion !== indice),
    );
    this.guardar();
  }

  setSiembra(fecha: string): void {
    this._siembra.set(fecha || hoy());
    this.guardar();
  }

  /** Payload para el disparo del agente en el paso 4. */
  aPayload(): {
    productos: { cultivo_codigo?: string; producto_texto?: string }[];
    siembra: string;
  } {
    return {
      productos: this._productos().map((producto) =>
        producto.codigo !== null
          ? { cultivo_codigo: producto.codigo }
          : { producto_texto: producto.texto },
      ),
      siembra: this._siembra(),
    };
  }

  limpiar(): void {
    this._productos.set([]);
    this._siembra.set(hoy());
    this.guardar();
  }

  private guardar(): void {
    const proyectoId = this._proyectoId();
    if (proyectoId === '') return;
    try {
      const borrador: Borrador = {
        proyectoId,
        productos: this._productos(),
        siembra: this._siembra(),
      };
      localStorage.setItem(CLAVE, JSON.stringify(borrador));
    } catch {
      // Sin almacenamiento (modo privado o SSR): el borrador vive en memoria.
    }
  }
}

function leer(proyectoId: string): Borrador | null {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (crudo === null) return null;
    const borrador = JSON.parse(crudo) as Borrador;
    return borrador.proyectoId === proyectoId ? borrador : null;
  } catch {
    return null;
  }
}

/** Hoy en formato `YYYY-MM-DD`, que es lo que espera el backend. */
function hoy(): string {
  const ahora = new Date();
  const mes = `${ahora.getMonth() + 1}`.padStart(2, '0');
  const dia = `${ahora.getDate()}`.padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}
