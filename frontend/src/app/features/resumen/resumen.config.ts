/**
 * Palanca de desarrollo: mientras se prueban cambios del motor hace falta volver a
 * generar el informe con el mismo borrador. Con esto en `true`, el botón "Regenerar"
 * funciona sin plan premium y el backend corre una corrida nueva en vez de reutilizar
 * la del mismo intake.
 *
 * Al dar el visto bueno: poner en `false` para restaurar el comportamiento de producto
 * (una sola generación, regenerar es plan premium).
 */
export const PERMITIR_REGENERAR = true;
