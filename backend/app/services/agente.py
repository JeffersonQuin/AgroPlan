"""Corridas del agente y documento final del proyecto (paso 4).

El agente recibe un intake normalizado y devuelve una propuesta sin geometría. El
motor determinístico sigue siendo el único que calcula polígonos, sectores y red.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agente import PROMPT_VERSION, ContextoAgente
from app.agente import ejecutar as ejecutar_agente
from app.agente.validacion import repartir_porcentajes
from app.models.agente import AgenteCorrida, AgenteFuente, AgenteRecomendacion
from app.models.enums import (
    EstadoCorrida,
    FuenteAgua,
    TipoRecomendacion,
)
from app.models.proyecto import Proyecto, Terreno
from app.repository import agente_corrida as agente_corrida_repo
from app.repository import agente_fuente as agente_fuente_repo
from app.repository import agente_recomendacion as agente_recomendacion_repo
from app.repository import cultivo as cultivo_repo
from app.repository import proyecto as proyecto_repo
from app.repository import proyecto_cultivo as bloque_repo
from app.repository import sistema_riego as sistema_riego_repo
from app.repository import suelo as suelo_repo
from app.repository import terreno as terreno_repo
from app.schemas.agente import (
    BloqueGenerado,
    CorridaDetalleOut,
    CorridaOut,
    DisenoGenerado,
    EntradaAgente,
    FuenteOut,
    ProductoDeseado,
    PropuestaAgente,
    RecomendacionOut,
    RecomendacionUpdate,
    ResultadoProyectoOut,
)
from app.schemas.comun import Advertencia, Punto
from app.schemas.cultivo import BloqueCultivoCreate, ModoReparto
from app.schemas.riego import EmisorIn, SistemaRiegoIn
from app.services import cultivo as cultivo_service
from app.services import geometria
from app.services import proyecto as proyecto_service
from app.services import riego as riego_service

__all__ = [
    "PROMPT_VERSION",
    "AgenteServiceError",
    "InicioCorrida",
    "actualizar_recomendacion",
    "aplicar_corrida",
    "ejecutar_corrida",
    "iniciar_corrida",
    "listar_corridas",
    "listar_fuentes",
    "listar_recomendaciones",
    "obtener_corrida",
    "resultado_proyecto",
]


class AgenteServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _terreno_requerido(db: Session, proyecto: Proyecto) -> Terreno:
    terreno = terreno_repo.get_by_proyecto(db, proyecto.id)
    if terreno is None:
        raise AgenteServiceError(
            422, "Primero define el terreno antes de ejecutar el agente"
        )
    return terreno


def _productos_desde_bloques(db: Session, proyecto: Proyecto) -> list[ProductoDeseado]:
    bloques = bloque_repo.list_by_proyecto(db, proyecto.id)
    if not bloques:
        raise AgenteServiceError(
            422, "Asigna al menos un cultivo antes de ejecutar el agente"
        )

    agrupados: dict[str, dict] = {}
    for bloque in bloques:
        actual = agrupados.setdefault(
            bloque.cultivo_codigo,
            {
                "prioridad": bloque.orden,
                "area": 0.0,
            },
        )
        actual["prioridad"] = min(actual["prioridad"], bloque.orden)
        actual["area"] += float(bloque.area_m2)

    productos: list[ProductoDeseado] = []
    for codigo, datos in sorted(agrupados.items(), key=lambda item: item[1]["prioridad"]):
        cultivo = cultivo_repo.get_by_codigo(db, codigo)
        productos.append(
            ProductoDeseado(
                nombre=cultivo.nombre if cultivo is not None else codigo,
                prioridad=datos["prioridad"],
                area_deseada_m2=round(datos["area"], 2) or None,
            )
        )
    return productos


@dataclass(slots=True)
class InicioCorrida:
    """Corrida vigente pedida por el usuario y si hay que ejecutarla ahora."""

    corrida_id: uuid.UUID
    estado: str
    intake_hash: str
    creada: bool


def _corrida_vigente(
    db: Session, proyecto: Proyecto, intake_hash: str
) -> AgenteCorrida | None:
    """Última corrida con el mismo intake: es la que se reutiliza."""

    for corrida in agente_corrida_repo.list_by_proyecto(db, proyecto.id):
        if corrida.intake_hash == intake_hash:
            return corrida
    return None


def iniciar_corrida(db: Session, proyecto: Proyecto) -> InicioCorrida:
    """Crea la corrida del intake actual o devuelve la vigente, sin ejecutarla.

    La ejecución la dispara el router como tarea de fondo: el request nunca espera al
    modelo. Repetir el pedido con el mismo intake no gasta otra llamada.
    """

    terreno = _terreno_requerido(db, proyecto)
    productos = _productos_desde_bloques(db, proyecto)

    entrada = EntradaAgente(
        proyecto_id=proyecto.id,
        productos=productos,
        area_m2=float(terreno.area_m2),
        suelo_codigo=terreno.suelo_codigo,
        fuente_agua=terreno.fuente_agua,
        caudal_efectivo_m3h=float(terreno.caudal_efectivo_m3h),
        caudal_origen=terreno.caudal_origen,
        zona=proyecto.zona,
        pendiente_pct=float(terreno.pendiente_pct),
    )
    huella = entrada.huella()

    vigente = _corrida_vigente(db, proyecto, huella)
    if vigente is not None:
        if vigente.estado == EstadoCorrida.OK.value:
            return InicioCorrida(
                corrida_id=vigente.id,
                estado=vigente.estado,
                intake_hash=vigente.intake_hash,
                creada=False,
            )
        if vigente.estado in (
            EstadoCorrida.PENDIENTE.value,
            EstadoCorrida.CORRIENDO.value,
        ):
            raise AgenteServiceError(
                409, "Ya hay una corrida en curso para este intake"
            )

    corrida = AgenteCorrida(
        proyecto_id=proyecto.id,
        usuario_id=proyecto.usuario_id,
        estado=EstadoCorrida.PENDIENTE.value,
        entrada=entrada.model_dump(mode="json"),
        intake_hash=huella,
        motor_version=riego_service.MOTOR_VERSION,
        prompt_version=PROMPT_VERSION,
    )
    corrida = agente_corrida_repo.create(db, corrida)

    # El proyecto apunta a su corrida vigente para que el front sepa qué polling
    # retomar al reabrir el wizard.
    proyecto.corrida_actual_id = corrida.id
    proyecto_repo.update(db, proyecto)

    return InicioCorrida(
        corrida_id=corrida.id,
        estado=corrida.estado,
        intake_hash=corrida.intake_hash,
        creada=True,
    )


def _contexto_desde_corrida(
    db: Session, proyecto: Proyecto, entrada: EntradaAgente
) -> ContextoAgente:
    """Lee de la base lo que el agente puede mirar. Nunca lo que él mismo escribió."""

    cultivos = cultivo_repo.list_all(db, solo_activos=True)
    suelo = suelo_repo.get_by_codigo(db, entrada.suelo_codigo)
    sistema = sistema_riego_repo.get_by_proyecto(db, proyecto.id)

    return ContextoAgente(
        entrada=entrada,
        catalogo=[
            {
                "codigo": cultivo.codigo,
                "nombre": cultivo.nombre,
                "color": cultivo.color,
                "demanda_agua_l_m2_dia": float(cultivo.demanda_agua_l_m2_dia),
                "ciclo_dias": cultivo.ciclo_dias,
            }
            for cultivo in cultivos
        ],
        suelo=(
            {
                "codigo": suelo.codigo,
                "nombre": suelo.nombre,
                "infiltracion_mm_h": float(suelo.infiltracion_mm_h),
            }
            if suelo is not None
            else None
        ),
        riego_actual=(
            {
                "tipo": sistema.tipo,
                "emisor_caudal_lh": float(sistema.emisor_caudal_lh),
                "num_sectores": sistema.num_sectores,
            }
            if sistema is not None
            else None
        ),
        bloques=len(bloque_repo.list_by_proyecto(db, proyecto.id)),
    )


def _persistir_fuentes(
    db: Session, corrida: AgenteCorrida, fuentes: list
) -> None:
    ahora = datetime.now(timezone.utc)
    for fuente in fuentes:
        agente_fuente_repo.add(
            db,
            AgenteFuente(
                corrida_id=corrida.id,
                tipo=fuente.tipo,
                titulo=(fuente.titulo or None),
                url=fuente.url,
                fragmento=(fuente.fragmento or None),
                recuperado_en=ahora,
            ),
        )


def _persistir_recomendaciones(
    db: Session, corrida: AgenteCorrida, propuesta: PropuestaAgente
) -> None:
    filas: list[tuple[str, dict, str | None]] = [
        (
            TipoRecomendacion.CULTIVO.value,
            cultivo.model_dump(mode="json"),
            cultivo.justificacion,
        )
        for cultivo in propuesta.cultivos
    ]
    filas.append(
        (
            TipoRecomendacion.SISTEMA_RIEGO.value,
            propuesta.sistema.model_dump(mode="json"),
            "Parámetros de riego propuestos para el terreno y el caudal disponibles.",
        )
    )
    filas.extend(
        (
            TipoRecomendacion.ADVERTENCIA.value,
            alerta.model_dump(mode="json"),
            alerta.mensaje,
        )
        for alerta in propuesta.advertencias
    )

    for tipo, payload, justificacion in filas:
        agente_recomendacion_repo.add(
            db,
            AgenteRecomendacion(
                corrida_id=corrida.id,
                tipo=tipo,
                payload=payload,
                justificacion=justificacion,
                confianza=None,
                aplicada=False,
            ),
        )


def ejecutar_corrida(db: Session, corrida_id: uuid.UUID, proyecto_id: uuid.UUID) -> None:
    """Corre el agente y congela el resultado. Pensada como tarea de fondo.

    El request ya respondió 202, así que la sesión llega abierta y acá empieza una
    transacción nueva. Nunca deja la corrida en ``corriendo``: pasa a ``ok`` o a
    ``error`` con ``error_detalle``.
    """

    corrida = agente_corrida_repo.get_by_id(db, corrida_id, proyecto_id)
    if corrida is None or corrida.estado != EstadoCorrida.PENDIENTE.value:
        return

    proyecto = proyecto_repo.get_by_id(db, proyecto_id)
    if proyecto is None:
        corrida.estado = EstadoCorrida.ERROR.value
        corrida.error_detalle = "El proyecto ya no existe"
        corrida.terminado_en = datetime.now(timezone.utc)
        agente_corrida_repo.update(db, corrida)
        return

    corrida.estado = EstadoCorrida.CORRIENDO.value
    corrida = agente_corrida_repo.update(db, corrida)

    inicio = time.monotonic()
    try:
        entrada = EntradaAgente.model_validate(corrida.entrada)
        resultado = ejecutar_agente(_contexto_desde_corrida(db, proyecto, entrada))
    except Exception as exc:  # noqa: BLE001 - una corrida rota no cae el proceso
        corrida.estado = EstadoCorrida.ERROR.value
        corrida.error_detalle = str(exc)[:2000] or exc.__class__.__name__
        corrida.duracion_ms = int((time.monotonic() - inicio) * 1000)
        corrida.terminado_en = datetime.now(timezone.utc)
        agente_corrida_repo.update(db, corrida)
        return

    corrida.salida = resultado.propuesta.model_dump(mode="json")
    corrida.modelo = resultado.modelo
    corrida.tokens_entrada = resultado.tokens_entrada
    corrida.tokens_salida = resultado.tokens_salida
    corrida.duracion_ms = int((time.monotonic() - inicio) * 1000)
    corrida.terminado_en = datetime.now(timezone.utc)
    corrida.estado = EstadoCorrida.OK.value
    corrida = agente_corrida_repo.update(db, corrida)

    _persistir_fuentes(db, corrida, resultado.fuentes)
    _persistir_recomendaciones(db, corrida, resultado.propuesta)


def _punto_conexion(terreno: Terreno) -> Punto:
    """Punto de conexión por defecto del terreno: esquina inferior del contorno."""

    vertices = (terreno.geometria or {}).get("vertices") or []
    try:
        puntos = geometria.normalizar_vertices(vertices)
    except (KeyError, TypeError, ValueError):
        return Punto(x=0, y=0)
    if not puntos:
        return Punto(x=0, y=0)
    x_min, y_min, _, _ = geometria.caja(puntos)
    return Punto(x=float(x_min), y=float(y_min))


def aplicar_corrida(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> ResultadoProyectoOut:
    """Materializa la propuesta congelada: bloques, riego y red.

    Es el único paso que escribe en el proyecto, y lo hace solo si el usuario lo pide
    explícitamente (``POST .../aplicar``). Repetirlo devuelve 409.
    """

    corrida = _corrida_requerida(db, proyecto, corrida_id)
    if corrida.estado != EstadoCorrida.OK.value or not corrida.salida:
        raise AgenteServiceError(
            409, "La corrida todavía no tiene una propuesta para aplicar"
        )

    aplicadas = [
        recomendacion
        for recomendacion in agente_recomendacion_repo.list_by_corrida(db, corrida.id)
        if recomendacion.aplicada
    ]
    if aplicadas:
        raise AgenteServiceError(409, "La corrida ya está aplicada")

    try:
        propuesta = PropuestaAgente.model_validate(corrida.salida)
    except ValueError as exc:
        raise AgenteServiceError(
            409, "La propuesta congelada de la corrida es inválida"
        ) from exc

    terreno = _terreno_requerido(db, proyecto)

    # La propuesta reemplaza el reparto anterior: los bloques se recrean desde el
    # snapshot congelado, no se parchean sobre la geometría que dibujó el usuario.
    for bloque in bloque_repo.list_by_proyecto(db, proyecto.id):
        cultivo_service.eliminar_bloque(db, proyecto, bloque.id)

    porcentajes = repartir_porcentajes(
        [cultivo.area_m2 for cultivo in propuesta.cultivos],
        float(terreno.area_m2),
    )
    for cultivo, porcentaje in zip(propuesta.cultivos, porcentajes, strict=True):
        if porcentaje <= 0:
            continue
        try:
            cultivo_service.crear_bloque(
                db,
                proyecto,
                BloqueCultivoCreate(
                    cultivo_codigo=cultivo.cultivo_codigo,
                    etiqueta=cultivo.nombre,
                    siembra=cultivo.siembra_sugerida,
                    cosecha=cultivo.cosecha_sugerida,
                    demanda_l_m2_dia=cultivo.demanda_l_m2_dia,
                    modo=ModoReparto.PORCENTAJE,
                    porcentaje=porcentaje,
                ),
            )
        except cultivo_service.CultivoServiceError as exc:
            raise AgenteServiceError(exc.status_code, exc.detail) from exc

    sistema = propuesta.sistema
    try:
        riego_service.upsert_config(
            db,
            proyecto,
            SistemaRiegoIn(
                tipo=sistema.tipo,
                fuente_agua=FuenteAgua(terreno.fuente_agua),
                tanque_l=sistema.tanque_l,
                bomba_hp=sistema.bomba_hp,
                emisor=EmisorIn(
                    tipo=sistema.emisor.tipo,
                    caudal_lh=sistema.emisor.caudal_lh,
                    separacion_m=sistema.emisor.separacion_m,
                ),
                separacion_laterales_m=sistema.separacion_laterales_m,
                punto_conexion=_punto_conexion(terreno),
                num_sectores=sistema.num_sectores,
            ),
        )
        riego_service.generar(db, proyecto)
    except riego_service.RiegoServiceError as exc:
        # El sistema de riego es válido aunque el motor no pueda cerrar la red: la
        # propuesta aplicada se conserva y el motivo se reporta como advertencia.
        propuesta.advertencias.append(
            Advertencia(
                codigo="RED_NO_GENERADA",
                mensaje=exc.detail[:300],
                campo="riego",
            )
        )

    ahora = datetime.now(timezone.utc)
    for recomendacion in agente_recomendacion_repo.list_by_corrida(db, corrida.id):
        recomendacion.aplicada = True
        recomendacion.aplicada_en = ahora
        agente_recomendacion_repo.update(db, recomendacion)

    proyecto.corrida_actual_id = corrida.id
    proyecto_repo.update(db, proyecto)

    resultado = resultado_proyecto(db, proyecto)
    resultado.advertencias.extend(
        alerta
        for alerta in propuesta.advertencias
        if alerta.codigo == "RED_NO_GENERADA"
    )
    return resultado


def listar_corridas(db: Session, proyecto: Proyecto) -> list[CorridaOut]:
    return [
        CorridaOut.model_validate(corrida)
        for corrida in agente_corrida_repo.list_by_proyecto(db, proyecto.id)
    ]


def obtener_corrida(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> CorridaDetalleOut:
    corrida = agente_corrida_repo.get_by_id(db, corrida_id, proyecto.id)
    if corrida is None:
        raise AgenteServiceError(404, "Corrida del agente no encontrada")

    fuentes = [
        FuenteOut.model_validate(fuente)
        for fuente in agente_fuente_repo.list_by_corrida(db, corrida.id)
    ]
    detalle = CorridaDetalleOut.model_validate(corrida)
    return detalle.model_copy(update={"fuentes": fuentes})


def resultado_proyecto(db: Session, proyecto: Proyecto) -> ResultadoProyectoOut:
    try:
        diseno = riego_service.obtener_diseno(db, proyecto)
    except riego_service.RiegoServiceError as exc:
        raise AgenteServiceError(exc.status_code, exc.detail) from exc

    bloques = []
    for bloque in bloque_repo.list_by_proyecto(db, proyecto.id):
        cultivo = cultivo_repo.get_by_codigo(db, bloque.cultivo_codigo)
        try:
            puntos = geometria.normalizar_vertices(bloque.poligono.get("anillo", []))
        except (KeyError, TypeError, ValueError):
            continue
        bloques.append(
            BloqueGenerado(
                id=bloque.id,
                cultivo_codigo=bloque.cultivo_codigo,
                color=cultivo.color if cultivo is not None else "#4CAF50",
                poligono=geometria.poligono_dict(puntos),
                area_m2=float(bloque.area_m2),
                centroide=geometria.punto_dict(geometria.centroide(puntos)),
            )
        )

    return ResultadoProyectoOut(
        proyecto_id=proyecto.id,
        nombre=proyecto.nombre,
        estado=proyecto.estado,
        diseno=DisenoGenerado(
            bloques=bloques,
            sistema=diseno.sistema,
            sectores=diseno.sectores,
            red=diseno.red,
            computo=diseno.computo,
            advertencias=diseno.advertencias,
        ),
        advertencias=diseno.advertencias,
    )


# --------------------------------------------------------------------------- #
# Fuentes y recomendaciones de una corrida
# --------------------------------------------------------------------------- #


def _corrida_requerida(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> AgenteCorrida:
    corrida = agente_corrida_repo.get_by_id(db, corrida_id, proyecto.id)
    if corrida is None:
        raise AgenteServiceError(404, "Corrida del agente no encontrada")
    return corrida


def obtener_corrida_del_usuario(
    db: Session, usuario, corrida_id: uuid.UUID
) -> CorridaDetalleOut:
    """Polling sin conocer el proyecto: ``GET /agente/corridas/{corrida_id}``."""

    corrida = agente_corrida_repo.get_by_id(db, corrida_id)
    if corrida is None:
        raise AgenteServiceError(404, "Corrida del agente no encontrada")
    try:
        proyecto = proyecto_service.get_proyecto(db, corrida.proyecto_id, usuario)
    except proyecto_service.ProyectoServiceError as exc:
        raise AgenteServiceError(exc.status_code, exc.detail) from exc
    return obtener_corrida(db, proyecto, corrida.id)


def listar_fuentes(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> list[FuenteOut]:
    corrida = _corrida_requerida(db, proyecto, corrida_id)
    return [
        FuenteOut.model_validate(fuente)
        for fuente in agente_fuente_repo.list_by_corrida(db, corrida.id)
    ]


def listar_recomendaciones(
    db: Session, proyecto: Proyecto, corrida_id: uuid.UUID
) -> list[RecomendacionOut]:
    corrida = _corrida_requerida(db, proyecto, corrida_id)
    return [
        RecomendacionOut.model_validate(recomendacion)
        for recomendacion in agente_recomendacion_repo.list_by_corrida(
            db, corrida.id
        )
    ]


def actualizar_recomendacion(
    db: Session,
    proyecto: Proyecto,
    corrida_id: uuid.UUID,
    recomendacion_id: uuid.UUID,
    data: RecomendacionUpdate,
) -> RecomendacionOut:
    corrida = _corrida_requerida(db, proyecto, corrida_id)
    recomendacion = agente_recomendacion_repo.get_by_id(
        db, recomendacion_id, corrida.id
    )
    if recomendacion is None:
        raise AgenteServiceError(404, "Recomendación del agente no encontrada")

    recomendacion.aplicada = data.aplicada
    recomendacion.aplicada_en = (
        datetime.now(timezone.utc) if data.aplicada else None
    )
    recomendacion = agente_recomendacion_repo.update(db, recomendacion)
    return RecomendacionOut.model_validate(recomendacion)
