"""Corridas del agente y documento final del proyecto (paso 4).

El agente recibe un intake normalizado y devuelve una propuesta sin geometría. El
motor determinístico sigue siendo el único que calcula polígonos, sectores y red.
"""

from __future__ import annotations

import math
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agente import PROMPT_VERSION, ContextoAgente
from app.agente import ejecutar as ejecutar_agente
from app.agente import fichas as fichas_agente
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
    AjusteMotor,
    BloqueGenerado,
    CalendarioBloque,
    CifrasMotor,
    CorridaDetalleOut,
    CorridaOut,
    DisenoGenerado,
    EntradaAgente,
    FichaFuente,
    FuenteOut,
    ProductoDeseado,
    ProductoSolicitado,
    PropuestaAgente,
    RecomendacionInforme,
    RecomendacionOut,
    RecomendacionUpdate,
    RestriccionesEntrada,
    ResultadoProyectoOut,
)
from app.schemas.comun import Advertencia, Punto
from app.schemas.cultivo import BloqueCultivoCreate, ModoReparto
from app.schemas.proyecto import GeometriaTerreno
from app.schemas.riego import EmisorIn, SistemaRiegoIn
from app.services import cultivo as cultivo_service
from app.services import geometria
from app.services import proyecto as proyecto_service
from app.services import riego as riego_service
from app.services import terreno as terreno_service

__all__ = [
    "PROMPT_VERSION",
    "AgenteServiceError",
    "InicioCorrida",
    "actualizar_recomendacion",
    "aplicar_corrida",
    "aplicar_corrida_del_usuario",
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


def _tomar(catalogo, ficha, campo):
    """Dato del catálogo; si falta, el de la ficha curada. ``None`` si no está.

    El catálogo manda porque es la ficha revisada que ve el paso 2. El curado cubre
    los campos que una fila vieja del catálogo todavía no tiene.
    """

    valor = getattr(catalogo, campo, None)
    if valor is not None and valor != []:
        return valor
    if ficha is not None:
        valor = getattr(ficha, campo, None)
        if valor is not None and valor != []:
            return valor
    return None


def _fuentes_ficha(valor) -> list[FichaFuente] | None:
    """Normaliza las fuentes del catálogo y del curado al contrato de la entrada."""

    if not valor:
        return None
    fuentes: list[FichaFuente] = []
    for item in valor:
        if isinstance(item, dict):
            tipo = item.get("tipo")
            titulo = item.get("titulo")
            url = item.get("url")
            fragmento = item.get("fragmento")
        else:
            tipo = getattr(item, "tipo", None)
            titulo = getattr(item, "titulo", None)
            url = getattr(item, "url", None)
            fragmento = getattr(item, "fragmento", None)
        if not isinstance(tipo, str) or not tipo:
            continue
        fuentes.append(
            FichaFuente(
                tipo=tipo[:30],
                titulo=(str(titulo)[:300] if titulo else None),
                url=(str(url)[:1000] if url else None),
                fragmento=(str(fragmento)[:1000] if fragmento else None),
            )
        )
    return fuentes or None


def _producto_deseado(
    cultivo,
    *,
    prioridad: int,
    area_deseada_m2: float | None = None,
    nombre: str | None = None,
) -> ProductoDeseado:
    """Arma un producto con toda la ficha que la base ya tiene modelada (S5)."""

    ficha = fichas_agente.buscar(cultivo.codigo)
    kc = _tomar(cultivo, ficha, "kc")
    raiz = _tomar(cultivo, ficha, "profundidad_raiz_cm")
    densidad = _tomar(cultivo, ficha, "densidad_plantas_m2")
    meses = _tomar(cultivo, ficha, "meses_siembra")
    aptitud = _tomar(cultivo, ficha, "aptitud_suelo")
    fuentes = _tomar(cultivo, ficha, "fuentes")

    return ProductoDeseado(
        nombre=nombre or cultivo.nombre,
        cultivo_codigo=cultivo.codigo,
        prioridad=prioridad,
        area_deseada_m2=area_deseada_m2,
        kc=float(kc) if kc is not None else None,
        profundidad_raiz_cm=int(raiz) if raiz is not None else None,
        densidad_plantas_m2=float(densidad) if densidad is not None else None,
        meses_siembra=list(meses) if meses is not None else None,
        aptitud_suelo=aptitud or None,
        fuentes=_fuentes_ficha(fuentes),
    )


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
            _producto_deseado(
                cultivo,
                prioridad=datos["prioridad"],
                area_deseada_m2=round(datos["area"], 2) or None,
                nombre=cultivo.nombre,
            )
            if cultivo is not None
            else ProductoDeseado(
                nombre=codigo,
                prioridad=datos["prioridad"],
                area_deseada_m2=round(datos["area"], 2) or None,
            )
        )
    return productos


def _productos_desde_lista(
    db: Session, proyecto: Proyecto, productos: list[ProductoSolicitado]
) -> list[ProductoDeseado]:
    """Resuelve la lista que armó el usuario: código de catálogo o producto nuevo.

    Un producto que no está en el catálogo se investiga acá mismo (ficha curada
    primero, web de respaldo) y queda dado de alta, igual que en el paso 2 anterior.
    """

    resueltos: list[ProductoDeseado] = []
    for indice, pedido in enumerate(productos):
        prioridad = pedido.prioridad or indice + 1

        if pedido.cultivo_codigo:
            cultivo = cultivo_repo.get_by_codigo(db, pedido.cultivo_codigo)
            if cultivo is None or not cultivo.activo:
                raise AgenteServiceError(
                    422, f"El cultivo '{pedido.cultivo_codigo}' no existe o está inactivo"
                )
            resueltos.append(_producto_deseado(cultivo, prioridad=prioridad))
            continue

        if not pedido.producto_texto:
            raise AgenteServiceError(422, "Cada producto necesita un nombre")

        cultivo, advertencias = cultivo_service._resolver_producto(
            db, pedido.producto_texto
        )
        if cultivo is None:
            mensaje = advertencias[0].mensaje if advertencias else "Producto no reconocido"
            raise AgenteServiceError(422, mensaje)
        resueltos.append(_producto_deseado(cultivo, prioridad=prioridad))

    return resueltos


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


def iniciar_corrida(
    db: Session,
    proyecto: Proyecto,
    *,
    productos: list[ProductoSolicitado] | None = None,
    siembra=None,
    restricciones: RestriccionesEntrada | None = None,
) -> InicioCorrida:
    """Crea la corrida del intake actual o devuelve la vigente, sin ejecutarla.

    ``productos`` es la lista que armó el usuario en el paso 2: el agente reparte el
    área entre esos productos. Si no llega, se usan los bloques ya asignados (camino
    anterior). La siembra y las ``restricciones`` del paso 3 viajan al agente y
    quedan congeladas con la corrida.

    La ejecución la dispara el router como tarea de fondo: el request nunca espera al
    modelo. Repetir el pedido con el mismo intake no gasta otra llamada.
    """

    terreno = _terreno_requerido(db, proyecto)
    pedidos = productos or []
    elegidos = (
        _productos_desde_lista(db, proyecto, pedidos)
        if pedidos
        else _productos_desde_bloques(db, proyecto)
    )

    suelo = suelo_repo.get_by_codigo(db, terreno.suelo_codigo)
    medidas = terreno_service.terreno_out(terreno)

    entrada = EntradaAgente(
        proyecto_id=proyecto.id,
        productos=elegidos,
        area_m2=float(terreno.area_m2),
        suelo_codigo=terreno.suelo_codigo,
        fuente_agua=terreno.fuente_agua,
        caudal_efectivo_m3h=float(terreno.caudal_efectivo_m3h),
        caudal_origen=terreno.caudal_origen,
        zona=proyecto.zona,
        pendiente_pct=float(terreno.pendiente_pct),
        siembra=siembra,
        infiltracion_mm_h=(
            float(suelo.infiltracion_mm_h) if suelo is not None else None
        ),
        retencion_agua_mm_m=(
            float(suelo.retencion_agua_mm_m)
            if suelo is not None and suelo.retencion_agua_mm_m is not None
            else None
        ),
        lados_m=medidas.lados_m or None,
        geometria=GeometriaTerreno.model_validate(terreno.geometria),
        perimetro_m=float(terreno.perimetro_m),
        profundidad_nivel_dinamico_m=(
            float(terreno.profundidad_nivel_dinamico_m)
            if terreno.profundidad_nivel_dinamico_m is not None
            else None
        ),
        restricciones=restricciones,
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
    db: Session,
    proyecto: Proyecto,
    entrada: EntradaAgente,
    corrida_id: uuid.UUID | None = None,
) -> ContextoAgente:
    """Lee de la base lo que el agente puede mirar. Nunca lo que él mismo escribió."""

    cultivos = cultivo_repo.list_all(db, solo_activos=True)
    suelo = suelo_repo.get_by_codigo(db, entrada.suelo_codigo)
    sistema = sistema_riego_repo.get_by_proyecto(db, proyecto.id)

    catalogo = []
    for cultivo in cultivos:
        ficha = fichas_agente.buscar(cultivo.codigo)
        kc = _tomar(cultivo, ficha, "kc")
        raiz = _tomar(cultivo, ficha, "profundidad_raiz_cm")
        densidad = _tomar(cultivo, ficha, "densidad_plantas_m2")
        meses = _tomar(cultivo, ficha, "meses_siembra")
        aptitud = _tomar(cultivo, ficha, "aptitud_suelo")
        fuentes = _tomar(cultivo, ficha, "fuentes")
        catalogo.append(
            {
                "codigo": cultivo.codigo,
                "nombre": cultivo.nombre,
                "color": cultivo.color,
                "demanda_agua_l_m2_dia": float(cultivo.demanda_agua_l_m2_dia),
                "ciclo_dias": cultivo.ciclo_dias,
                "kc": float(kc) if kc is not None else None,
                "aptitud_suelo": aptitud or None,
                "profundidad_raiz_cm": int(raiz) if raiz is not None else None,
                "densidad_plantas_m2": (
                    float(densidad) if densidad is not None else None
                ),
                "meses_siembra": list(meses) if meses is not None else None,
                "fuentes": (
                    [
                        {
                            "tipo": fuente.tipo,
                            "titulo": fuente.titulo,
                            "url": fuente.url,
                            "fragmento": fuente.fragmento,
                        }
                        for fuente in _fuentes_ficha(fuentes) or []
                    ]
                    or None
                ),
            }
        )

    return ContextoAgente(
        entrada=entrada,
        catalogo=catalogo,
        suelo=(
            {
                "codigo": suelo.codigo,
                "nombre": suelo.nombre,
                "infiltracion_mm_h": float(suelo.infiltracion_mm_h),
                "retencion_agua_mm_m": (
                    float(suelo.retencion_agua_mm_m)
                    if suelo.retencion_agua_mm_m is not None
                    else None
                ),
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
        sesion=str(corrida_id),
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

    # Todo lo que puede fallar por validación se arma antes de tocar el proyecto: si
    # el payload no valida, no se borró ni un bloque.
    porcentajes = repartir_porcentajes(
        [cultivo.area_m2 for cultivo in propuesta.cultivos],
        float(terreno.area_m2),
    )
    try:
        altas = [
            BloqueCultivoCreate(
                cultivo_codigo=cultivo.cultivo_codigo,
                etiqueta=cultivo.nombre,
                siembra=cultivo.siembra_sugerida,
                cosecha=cultivo.cosecha_sugerida,
                demanda_l_m2_dia=cultivo.demanda_l_m2_dia,
                modo=ModoReparto.PORCENTAJE,
                porcentaje=porcentaje,
            )
            for cultivo, porcentaje in zip(
                propuesta.cultivos, porcentajes, strict=True
            )
            if porcentaje > 0
        ]
        sistema = propuesta.sistema
        configuracion = SistemaRiegoIn(
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
        )
    except ValidationError as exc:
        raise AgenteServiceError(
            422, f"La propuesta congelada no se puede aplicar: {exc.errors()[0]['msg']}"
        ) from exc

    # La propuesta reemplaza el reparto anterior: los bloques se recrean desde el
    # snapshot congelado, no se parchean sobre la geometría que dibujó el usuario.
    for bloque in bloque_repo.list_by_proyecto(db, proyecto.id):
        cultivo_service.eliminar_bloque(db, proyecto, bloque.id)

    for alta in altas:
        try:
            cultivo_service.crear_bloque(db, proyecto, alta)
        except cultivo_service.CultivoServiceError as exc:
            raise AgenteServiceError(exc.status_code, exc.detail) from exc

    try:
        riego_service.upsert_config(db, proyecto, configuracion)
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
    recomendaciones = [
        RecomendacionOut.model_validate(recomendacion)
        for recomendacion in agente_recomendacion_repo.list_by_corrida(db, corrida.id)
    ]
    detalle = CorridaDetalleOut.model_validate(corrida)
    return detalle.model_copy(
        update={"fuentes": fuentes, "recomendaciones": recomendaciones}
    )


def _corrida_actual(db: Session, proyecto: Proyecto) -> AgenteCorrida | None:
    """Corrida vigente del proyecto: la que el informe usa como referencia."""

    if proyecto.corrida_actual_id is None:
        return None
    return agente_corrida_repo.get_by_id(db, proyecto.corrida_actual_id, proyecto.id)


def _propuesta_de_corrida(corrida: AgenteCorrida | None) -> PropuestaAgente | None:
    """Propuesta congelada, o None si la corrida todavía no terminó bien."""

    if corrida is None or corrida.estado != EstadoCorrida.OK.value or not corrida.salida:
        return None
    try:
        return PropuestaAgente.model_validate(corrida.salida)
    except ValueError:
        return None


def _texto(valor: float | None) -> str | None:
    """Formatea una cifra para el informe sin arrastrar decimales falsos."""

    if valor is None:
        return None
    if isinstance(valor, int):
        return str(valor)
    return f"{float(valor):g}"


def _difiere(
    valor_agente: float | None, valor_motor: float | None, tolerancia: float
) -> bool:
    """Solo hay ajuste si el agente informó una cifra y el motor la cambió de verdad.

    El borde exacto de la tolerancia no cuenta como diferencia: ``1.5`` contra
    ``1.55`` con tolerancia ``0.05`` es el mismo valor, no un ajuste. El ``eps``
    absorbe el error de coma flotante de esa comparación.
    """

    if valor_agente is None or valor_motor is None:
        return False
    return not math.isclose(
        float(valor_agente),
        float(valor_motor),
        rel_tol=0.0,
        abs_tol=tolerancia + 1e-9,
    )


def _cifras_motor(
    db: Session, proyecto: Proyecto, bloques: list, diseno: DisenoGenerado
) -> CifrasMotor:
    """Cifras hidráulicas que calcula el determinístico después de generar la red.

    El caudal por sector sale de los sectores **generados** (``sectores[].caudal_m3h``),
    no del caudal efectivo dividido entre sectores: la red reparte por goteros y área,
    así que los dos números pueden diferir. El preview queda como respaldo cuando
    todavía no hay red.
    """

    try:
        previa = riego_service.preview(db, proyecto)
    except riego_service.RiegoServiceError:
        previa = None

    caudal_sector = (
        max(float(sector.caudal_m3h) for sector in diseno.sectores)
        if diseno.sectores
        else (previa.caudal_sector_m3h if previa is not None else None)
    )
    demanda_pico = (
        sum(
            float(bloque.area_m2) * float(bloque.demanda_l_m2_dia)
            for bloque in bloques
        )
        if bloques
        else None
    )
    return CifrasMotor(
        presion_trabajo_bar=previa.presion_bar if previa is not None else None,
        caudal_sector_m3h=caudal_sector,
        tiempo_riego_h=(
            round(previa.tiempo_riego_min / 60.0, 2) if previa is not None else None
        ),
        autonomia_dias=previa.autonomia_dias if previa is not None else None,
        demanda_pico_l_dia=(
            round(demanda_pico, 2) if demanda_pico is not None else None
        ),
    )


def _normalizar_texto(valor: str) -> str:
    """Minúsculas y sin tildes, para comparar rubros y unidades del cómputo."""

    return valor.lower().translate(str.maketrans("áéíóúü", "aeiouu"))


# Unidades normalizadas: el agente puede escribir "m", "ML" o "Metro lineal".
_UNIDADES_METRO = {
    "m",
    "ml",
    "m.",
    "ml.",
    "metro",
    "metros",
    "metro lineal",
    "metros lineales",
}
_UNIDADES_UNIDAD = {
    "u",
    "un",
    "unidad",
    "unidades",
    "pza",
    "pzas",
    "pieza",
    "piezas",
}


def _familia_material(rubro: str) -> str | None:
    """Familia del cómputo que el motor sí calcula, a partir del rubro del agente.

    ``tanque``, ``bomba`` y ``conexiones`` quedan fuera a propósito: el motor no los
    computa y no hay contra qué contrastarlos.
    """

    texto = _normalizar_texto(rubro)
    if "gotero" in texto or "emisor" in texto:
        return "goteros"
    if "valvula" in texto:
        return "valvulas"
    tokens = set(re.findall(r"[a-z]+", texto))
    if "tuber" in texto or "pvc" in texto or "manguera" in texto or "pe" in tokens:
        return "tuberia"
    return None


def _unidad_normalizada(unidad: str) -> str:
    return " ".join(_normalizar_texto(unidad).split())


def _ajustes_materiales(
    propuesta: PropuestaAgente, diseno: DisenoGenerado
) -> list[AjusteMotor]:
    """Contrasta el cómputo del agente (tubería, goteros, válvulas) con el motor."""

    objetivos = {
        "tuberia": (
            "computo.tuberia_m",
            diseno.computo.tuberia_m,
            _UNIDADES_METRO,
            "El motor recalculó la tubería a partir de la red generada.",
        ),
        "goteros": (
            "computo.goteros_u",
            diseno.computo.goteros_u,
            _UNIDADES_UNIDAD,
            "El motor recalculó los goteros según la separación y el área de la red.",
        ),
        "valvulas": (
            "computo.valvulas_u",
            diseno.computo.valvulas_u,
            _UNIDADES_UNIDAD,
            "El motor calcula una válvula por sector generado.",
        ),
    }

    ajustes: list[AjusteMotor] = []
    for material in propuesta.materiales:
        familia = _familia_material(material.rubro)
        if familia is None:
            continue
        campo, valor_motor, unidades, motivo = objetivos[familia]
        if _unidad_normalizada(material.unidad) not in unidades:
            # Otra unidad (rollos, cajas): no hay comparación honesta que hacer.
            continue
        if _difiere(material.cantidad, float(valor_motor), 0.5):
            ajustes.append(
                AjusteMotor(
                    campo=campo,
                    valor_agente=_texto(material.cantidad),
                    valor_motor=_texto(valor_motor),
                    motivo=motivo,
                )
            )
    return ajustes


def _ajustes_turnos(
    turnos: list, sectores: list
) -> list[AjusteMotor]:
    """Compara cada turno del agente con el caudal real de su sector (S3).

    Un turno por cada sector que difiera, y también los desajustes de conjunto: un
    turno de un sector que la red no generó, o un sector generado sin turno.
    """

    if not turnos:
        return []

    caudales_lh = {
        sector.numero: float(sector.caudal_m3h) * 1000.0 for sector in sectores
    }
    cubiertos: set[int] = set()
    ajustes: list[AjusteMotor] = []

    for turno in turnos:
        cubiertos.add(turno.sector)
        caudal_motor = caudales_lh.get(turno.sector)
        if caudal_motor is None:
            ajustes.append(
                AjusteMotor(
                    campo=f"caudal_sector_lh.{turno.sector}",
                    valor_agente=_texto(turno.caudal_lh),
                    valor_motor=None,
                    motivo=(
                        f"El agente propuso un turno para el sector {turno.sector}, "
                        f"pero el motor generó {len(sectores)} sectores."
                    ),
                )
            )
            continue
        if _difiere(turno.caudal_lh, caudal_motor, 0.5):
            ajustes.append(
                AjusteMotor(
                    campo=f"caudal_sector_lh.{turno.sector}",
                    valor_agente=_texto(turno.caudal_lh),
                    valor_motor=_texto(round(caudal_motor, 2)),
                    motivo=(
                        "El motor recalcula el caudal del sector "
                        f"{turno.sector} con los goteros y el área de la red generada."
                    ),
                )
            )

    for numero in sorted(set(caudales_lh) - cubiertos):
        ajustes.append(
            AjusteMotor(
                campo=f"caudal_sector_lh.{numero}",
                valor_agente=None,
                valor_motor=_texto(round(caudales_lh[numero], 2)),
                motivo=(
                    f"El motor generó el sector {numero}, pero el agente no propuso "
                    "un turno para él."
                ),
            )
        )
    return ajustes


def _ajustes_motor(
    propuesta: PropuestaAgente | None,
    diseno: DisenoGenerado,
    cifras: CifrasMotor,
    bloques: list[BloqueGenerado],
) -> list[AjusteMotor]:
    """Compara lo que propuso el agente con lo que devolvió el motor (S3).

    Solo se comparan los datos que el agente efectivamente trajo: un valor ausente
    queda en ``None`` y no genera un ajuste inventado.
    """

    if propuesta is None:
        return []

    agente = propuesta.cifras
    motor_por_variable = (
        (
            "presion_trabajo_bar",
            agente.presion_trabajo_bar,
            cifras.presion_trabajo_bar,
            0.05,
            "El motor recalculó la presión de trabajo con la bomba y la red generada.",
        ),
        (
            "tiempo_riego_h",
            agente.tiempo_riego_h,
            cifras.tiempo_riego_h,
            0.05,
            "El motor recalcula el tiempo de riego con la demanda del área asignada.",
        ),
        (
            "autonomia_dias",
            agente.autonomia_dias,
            cifras.autonomia_dias,
            0.05,
            "El motor recalcula la autonomía del tanque con la demanda real del área.",
        ),
        (
            "demanda_pico_l_dia",
            agente.demanda_pico_l_dia,
            cifras.demanda_pico_l_dia,
            1.0,
            "El motor recalcula la demanda pico total con área y demanda de cada bloque.",
        ),
    )

    ajustes = [
        AjusteMotor(
            campo=campo,
            valor_agente=_texto(valor_agente),
            valor_motor=_texto(valor_motor),
            motivo=motivo,
        )
        for campo, valor_agente, valor_motor, tolerancia, motivo in motor_por_variable
        if _difiere(valor_agente, valor_motor, tolerancia)
    ]

    ajustes.extend(_ajustes_turnos(agente.turnos, diseno.sectores))

    if agente.turnos and len(agente.turnos) != len(diseno.sectores):
        ajustes.append(
            AjusteMotor(
                campo="sectores",
                valor_agente=str(len(agente.turnos)),
                valor_motor=str(len(diseno.sectores)),
                motivo=(
                    f"El agente propuso {len(agente.turnos)} turnos y el motor "
                    f"generó {len(diseno.sectores)} sectores con los parámetros de "
                    f"riego de la corrida (num_sectores="
                    f"{propuesta.sistema.num_sectores})."
                ),
            )
        )

    areas_motor: dict[str, float] = {}
    for bloque in bloques:
        areas_motor[bloque.cultivo_codigo] = (
            areas_motor.get(bloque.cultivo_codigo, 0.0) + bloque.area_m2
        )
    for cultivo in propuesta.cultivos:
        area_motor = areas_motor.get(cultivo.cultivo_codigo)
        if area_motor is None:
            continue
        if _difiere(
            cultivo.area_m2, area_motor, max(0.5, area_motor * 0.01)
        ):
            ajustes.append(
                AjusteMotor(
                    campo=f"area_m2.{cultivo.cultivo_codigo}",
                    valor_agente=_texto(cultivo.area_m2),
                    valor_motor=_texto(round(area_motor, 2)),
                    motivo=(
                        "El motor ajustó el área del bloque para que el reparto cubra el terreno."
                    ),
                )
            )

    ajustes.extend(_ajustes_materiales(propuesta, diseno))

    return ajustes


def _recomendaciones_informe(
    db: Session, corrida: AgenteCorrida | None, propuesta: PropuestaAgente | None
) -> list[RecomendacionInforme]:
    """Recomendaciones finales (S7): las persistidas y las de la corrida congelada."""

    recomendaciones: list[RecomendacionInforme] = []
    if propuesta is not None:
        recomendaciones.extend(
            RecomendacionInforme(
                tipo="final",
                titulo=recomendacion.titulo,
                detalle=recomendacion.detalle,
                justificacion=recomendacion.justificacion or None,
            )
            for recomendacion in propuesta.recomendaciones
        )

    if corrida is None:
        return recomendaciones

    for fila in agente_recomendacion_repo.list_by_corrida(db, corrida.id):
        payload = fila.payload or {}
        titulo = (
            payload.get("titulo")
            or payload.get("nombre")
            or payload.get("mensaje")
            or fila.tipo
        )
        detalle = payload.get("detalle") or payload.get("mensaje")
        recomendaciones.append(
            RecomendacionInforme(
                id=fila.id,
                tipo=fila.tipo,
                titulo=str(titulo)[:300],
                detalle=str(detalle)[:1000] if detalle else None,
                justificacion=fila.justificacion,
                aplicada=fila.aplicada,
            )
        )
    return recomendaciones


def resultado_proyecto(db: Session, proyecto: Proyecto) -> ResultadoProyectoOut:
    try:
        diseno = riego_service.obtener_diseno(db, proyecto)
    except riego_service.RiegoServiceError as exc:
        raise AgenteServiceError(exc.status_code, exc.detail) from exc

    terreno = _terreno_requerido(db, proyecto)
    corrida = _corrida_actual(db, proyecto)
    propuesta = _propuesta_de_corrida(corrida)
    bloques_db = bloque_repo.list_by_proyecto(db, proyecto.id)
    imagenes = (
        {cultivo.cultivo_codigo: cultivo.imagen_url for cultivo in propuesta.cultivos}
        if propuesta is not None
        else {}
    )

    bloques = []
    for bloque in bloques_db:
        cultivo = cultivo_repo.get_by_codigo(db, bloque.cultivo_codigo)
        try:
            puntos = geometria.normalizar_vertices(bloque.poligono.get("anillo", []))
        except (KeyError, TypeError, ValueError):
            continue
        area = float(bloque.area_m2)
        demanda = float(bloque.demanda_l_m2_dia)
        bloques.append(
            BloqueGenerado(
                id=bloque.id,
                cultivo_codigo=bloque.cultivo_codigo,
                color=cultivo.color if cultivo is not None else "#4CAF50",
                poligono=geometria.poligono_dict(puntos),
                area_m2=area,
                centroide=geometria.punto_dict(geometria.centroide(puntos)),
                nombre=bloque.etiqueta or (cultivo.nombre if cultivo is not None else None),
                porcentaje=(
                    round(area / float(terreno.area_m2) * 100.0, 2)
                    if float(terreno.area_m2) > 0
                    else None
                ),
                demanda_pico_l_dia=round(area * demanda, 2),
                siembra=bloque.siembra,
                cosecha=bloque.cosecha,
                ciclo_dias=cultivo.ciclo_dias if cultivo is not None else None,
                kc=(
                    float(cultivo.kc)
                    if cultivo is not None and cultivo.kc is not None
                    else None
                ),
                imagen_url=imagenes.get(bloque.cultivo_codigo)
                or getattr(cultivo, "imagen_url", None),
            )
        )

    cifras = _cifras_motor(db, proyecto, bloques_db, diseno)
    calendario = [
        CalendarioBloque(
            bloque_id=bloque.id,
            cultivo_codigo=bloque.cultivo_codigo,
            etiqueta=bloque.etiqueta,
            siembra=bloque.siembra,
            cosecha=bloque.cosecha,
        )
        for bloque in bloques_db
    ]

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
            cifras=cifras,
            cifras_agente=propuesta.cifras if propuesta is not None else None,
            eficiencia_pct=(
                propuesta.cifras.eficiencia_pct if propuesta is not None else None
            ),
            calendario=calendario,
            materiales=(
                list(propuesta.materiales) if propuesta is not None else []
            ),
            recomendaciones=_recomendaciones_informe(db, corrida, propuesta),
            fuentes=(
                [
                    FuenteOut.model_validate(fuente)
                    for fuente in agente_fuente_repo.list_by_corrida(db, corrida.id)
                ]
                if corrida is not None
                else []
            ),
            ajustes=_ajustes_motor(propuesta, diseno, cifras, bloques),
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


def _proyecto_de_corrida(db: Session, usuario, corrida_id: uuid.UUID) -> tuple:
    corrida = agente_corrida_repo.get_by_id(db, corrida_id)
    if corrida is None:
        raise AgenteServiceError(404, "Corrida del agente no encontrada")
    try:
        proyecto = proyecto_service.get_proyecto(db, corrida.proyecto_id, usuario)
    except proyecto_service.ProyectoServiceError as exc:
        raise AgenteServiceError(exc.status_code, exc.detail) from exc
    return corrida, proyecto


def obtener_corrida_del_usuario(
    db: Session, usuario, corrida_id: uuid.UUID
) -> CorridaDetalleOut:
    """Polling sin conocer el proyecto: ``GET /agente/corridas/{corrida_id}``."""

    corrida, proyecto = _proyecto_de_corrida(db, usuario, corrida_id)
    return obtener_corrida(db, proyecto, corrida.id)


def aplicar_corrida_del_usuario(
    db: Session, usuario, corrida_id: uuid.UUID
) -> ResultadoProyectoOut:
    """``POST /agente/corridas/{corrida_id}/aplicar``, la ruta del contrato."""

    _, proyecto = _proyecto_de_corrida(db, usuario, corrida_id)
    return aplicar_corrida(db, proyecto, corrida_id)


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
