import { HttpResponse } from '@angular/common/http';

/**
 * Descarga de archivos del paso 4 (S8).
 *
 * El PDF lo genera el backend y llega como `Blob`; el navegador lo baja con un
 * enlace efímero. Así el botón del header y el del informe comparten una sola
 * implementación.
 */
export function nombreDeArchivo(respuesta: HttpResponse<Blob>, proyectoId: string): string {
  const cabecera = respuesta.headers.get('Content-Disposition') ?? '';
  const coincidencia = /filename="?([^";]+)"?/i.exec(cabecera);
  const nombre = coincidencia?.[1]?.trim();
  return nombre !== undefined && nombre !== '' ? nombre : `informe-${proyectoId}.pdf`;
}

export function descargarBlob(blob: Blob, nombre: string): void {
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombre;
  enlace.rel = 'noopener';
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
}
