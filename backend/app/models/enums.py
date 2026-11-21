"""Dominios cerrados del producto AgroPlan.

Los valores son los que viajan por la API y quedan persistidos: cambiarlos es un
cambio de contrato. Los CHECK de cada tabla repiten la lista para que la base no
acepte valores fuera del dominio aunque se escriba por fuera del ORM.
"""

from enum import StrEnum


class UnidadSistema(StrEnum):
    """Sistema de unidades del proyecto. El motor solo calcula en métrico."""

    METRICO = "metric"
    IMPERIAL = "imperial"


class EstadoProyecto(StrEnum):
    BORRADOR = "borrador"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"


class FormaTerreno(StrEnum):
    RECTANGULO = "rectangulo"
    TRAPECIO = "trapecio"
    POLIGONO = "poligono"


class FuenteAgua(StrEnum):
    """Origen del agua disponible. Define el caudal de referencia del sistema."""

    PILA = "pila"
    POZO = "pozo"
    RED = "red"
    CISTERNA = "cisterna"
    TANQUE = "tanque"


class OrigenCaudal(StrEnum):
    """Procedencia del caudal efectivo del terreno.

    ``CLIENTE``: el usuario lo informó (``caudal_disponible_m3h`` no nulo).
    ``ASUMIDO``: lo asignó el sistema a partir de ``fuente_agua``.
    """

    CLIENTE = "cliente"
    ASUMIDO = "asumido"


class OrigenBloque(StrEnum):
    """Quién generó un bloque de cultivo: el usuario o el motor a partir del agente."""

    MANUAL = "manual"
    AGENTE = "agente"


class TipoSistemaRiego(StrEnum):
    GOTEO = "goteo"
    ASPERSION = "aspersion"
    INUNDACION = "inundacion"


class Orientacion(StrEnum):
    """Orientación de los laterales de riego."""

    ESTE_OESTE = "E-O"
    OESTE_ESTE = "O-E"
    NORTE_SUR = "N-S"
    SUR_NORTE = "S-N"


class TipoTramo(StrEnum):
    PRINCIPAL = "principal"
    SECUNDARIO = "secundario"
    LATERAL = "lateral"
    CONEXION = "conexion"


class TipoNodo(StrEnum):
    TANQUE = "tanque"
    BOMBA = "bomba"
    CABEZAL = "cabezal"
    VALVULA = "valvula"
    DERIVACION = "derivacion"
    HIDRANTE = "hidrante"


class EstadoCorrida(StrEnum):
    PENDIENTE = "pendiente"
    CORRIENDO = "corriendo"
    OK = "ok"
    ERROR = "error"
    DESCARTADA = "descartada"


class TipoRecomendacion(StrEnum):
    CULTIVO = "cultivo"
    DISTRIBUCION = "distribucion"
    SISTEMA_RIEGO = "sistema_riego"
    ADVERTENCIA = "advertencia"


class TipoFuenteAgente(StrEnum):
    """Tipo de procedencia de una fuente citada por el agente."""

    WEB = "web"
    CATALOGO_INTERNO = "catalogo_interno"
    NORMA = "norma"
    MANUAL = "manual"


# Listas para los CHECK de la base, derivadas del enum: una sola fuente de verdad.
VALORES_UNIDAD = tuple(item.value for item in UnidadSistema)
VALORES_ESTADO_PROYECTO = tuple(item.value for item in EstadoProyecto)
VALORES_FORMA_TERRENO = tuple(item.value for item in FormaTerreno)
VALORES_FUENTE_AGUA = tuple(item.value for item in FuenteAgua)
VALORES_ORIGEN_CAUDAL = tuple(item.value for item in OrigenCaudal)
VALORES_ORIGEN_BLOQUE = tuple(item.value for item in OrigenBloque)
VALORES_TIPO_SISTEMA = tuple(item.value for item in TipoSistemaRiego)
VALORES_ORIENTACION = tuple(item.value for item in Orientacion)
VALORES_TIPO_TRAMO = tuple(item.value for item in TipoTramo)
VALORES_TIPO_NODO = tuple(item.value for item in TipoNodo)
VALORES_ESTADO_CORRIDA = tuple(item.value for item in EstadoCorrida)
VALORES_TIPO_RECOMENDACION = tuple(item.value for item in TipoRecomendacion)
VALORES_TIPO_FUENTE_AGENTE = tuple(item.value for item in TipoFuenteAgente)
