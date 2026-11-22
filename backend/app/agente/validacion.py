"""Correcciones determinísticas sobre la propuesta cruda del modelo.

El modelo propone; el backend valida antes de aplicar. Cada corrección deja una
``Advertencia`` con código estable para que el front (y el usuario) sepa qué cambió:
``CULTIVO_FUERA_DE_CATALOGO``, ``AREA_AJUSTADA``, ``DEMANDA_AJUSTADA``,
``FECHAS_AJUSTADAS``, ``FUENTES_INCOMPLETAS`` y ``RIEGO_AJUSTADO``.

Nada de lo que hace este módulo depende del LLM: los mismos valores se corrigen igual
en modo catálogo y en modo modelo, y el resultado siempre valida contra
``app.schemas.agente.PropuestaAgente``.
"""

from __future__ import annotations

import unicodedata
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any

from app.schemas.agente import (
    CultivoRecomendado,
    EmisorRecomendado,
    PropuestaAgente,
    SistemaRecomendado,
)
from app.schemas.comun import Advertencia

# Dominios cerrados: los mismos CHECK de la base y de ``SistemaRiegoIn``.
CAUDALES_LH = (2.0, 4.0, 8.0)
BOMBAS_HP = (0.5, 1.0, 1.5, 2.0)
TIPOS_SISTEMA = ("goteo", "aspersion", "inundacion")
SEPARACION_MIN, SEPARACION_MAX = 0.2, 1.0
LATERALES_MIN, LATERALES_MAX = 0.5, 10.0
SECTORES_MIN, SECTORES_MAX = 1, 8
TANQUE_MAX_L = 1_000_000

# Si la demanda propuesta se aparta más de 25% de la del catálogo, manda el catálogo.
DESVIACION_DEMANDA = 0.25
CICLO_POR_DEFECTO = 90
AREA_MINIMA_M2 = 1.0
JUSTIFICACION_POR_DEFECTO = "Recomendado a partir del catálogo de cultivos de AgroPlan."


class PropuestaInvalida(Exception):
    """La propuesta no se puede corregir: no queda ningún cultivo utilizable."""


def _advertencia(
    codigo: str, mensaje: str, *, campo: str | None = None
) -> Advertencia:
    return Advertencia(codigo=codigo, mensaje=mensaje[:300], campo=campo)


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar nombres de cultivo."""

    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caracter for caracter in descompuesto if not unicodedata.combining(caracter)
    ).strip().lower()


def _mas_cercano(valor: float, permitidos: tuple[float, ...]) -> float:
    return min(permitidos, key=lambda candidato: (abs(candidato - valor), candidato))


def _limitar(valor: float, minimo: float, maximo: float) -> float:
    return round(min(max(valor, minimo), maximo), 2)


def _dec(valor: float) -> Decimal:
    return Decimal(str(valor))


def cuantizar_area(area: float, area_total: float) -> Decimal:
    """Baja el área a la grilla que el motor puede reproducir: 0,01% del terreno.

    ``aplicar`` escribe bloques con un porcentaje de dos decimales; si el área de la
    propuesta no cae en esa grilla, la geometría devuelve un área distinta, el intake
    cambia y volver a pedir el análisis gasta una corrida nueva. Cuantizar mantiene el
    ciclo estable sin tocar el motor.
    """

    if area_total <= 0:
        return _dec(area).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    quantum = _dec(area_total) / 10000
    return (_dec(area) / quantum).to_integral_value(rounding=ROUND_DOWN) * quantum


def repartir_porcentajes(areas: list[float], area_total: float) -> list[float]:
    """Porcentajes con dos decimales que nunca superan el 100% del terreno.

    El redondeo naive por cultivo puede sumar 100,01% y hacer que el último alta
    reviente contra ``le=100``. Acá se trunca cada cuota y el resto se reparte de a un
    centésimo, sin pasar del total real propuesto.
    """

    if area_total <= 0:
        raise ValueError("El área del terreno debe ser mayor que cero")
    if not areas:
        return []

    solicitado = sum(areas)
    if solicitado > area_total:
        # Precondición incumplida: se normaliza para no devolver más del 100%.
        areas = [area * area_total / solicitado for area in areas]

    crudos = [_dec(area) / _dec(area_total) * 100 for area in areas]
    centesimos = Decimal("0.01")
    objetivo = min(
        (sum(crudos) / centesimos).to_integral_value(rounding=ROUND_DOWN),
        Decimal(10000),
    )
    base = [int((crudo / centesimos).to_integral_value(rounding=ROUND_DOWN)) for crudo in crudos]

    sobrante = int(objetivo) - sum(base)
    orden = sorted(
        range(len(areas)),
        key=lambda indice: crudos[indice] - _dec(base[indice]) * centesimos,
        reverse=True,
    )
    for paso in range(max(sobrante, 0)):
        base[orden[paso % len(orden)]] += 1

    return [float(_dec(centesimos) * cantidad) for cantidad in base]


def _corregir_demanda(
    cultivo: CultivoRecomendado,
    referencia: float | None,
    advertencias: list[Advertencia],
) -> float:
    propuesta = cultivo.demanda_l_m2_dia
    if referencia is None:
        return _limitar(propuesta, 0.0, 20.0)

    referencia = _limitar(referencia, 0.0, 20.0)
    if referencia == 0:
        return propuesta if 0 <= propuesta <= 20 else referencia

    desvio = abs(propuesta - referencia) / referencia
    if desvio > DESVIACION_DEMANDA or not 0 <= propuesta <= 20:
        advertencias.append(
            _advertencia(
                "DEMANDA_AJUSTADA",
                f"La demanda de {cultivo.cultivo_codigo} pasó de {propuesta:g} a "
                f"{referencia:g} L/m²/día según el catálogo.",
                campo="demanda_l_m2_dia",
            )
        )
        return referencia
    return propuesta


def _corregir_fechas(
    cultivo: CultivoRecomendado,
    ciclo: int,
    advertencias: list[Advertencia],
    siembra_elegida: date | None = None,
) -> tuple[date | None, date | None]:
    # La fecha de siembra la elige el usuario: pisa lo que proponga el modelo.
    siembra = siembra_elegida or cultivo.siembra_sugerida
    cosecha = cultivo.cosecha_sugerida

    if siembra_elegida is not None and cultivo.siembra_sugerida != siembra_elegida:
        advertencias.append(
            _advertencia(
                "FECHAS_AJUSTADAS",
                f"Se usó la siembra elegida ({siembra_elegida.isoformat()}) en lugar de "
                f"la que propuso el agente.",
                campo="siembra_sugerida",
            )
        )

    if siembra is None and cosecha is not None:
        advertencias.append(
            _advertencia(
                "FECHAS_AJUSTADAS",
                f"{cultivo.cultivo_codigo} tenía cosecha sin siembra: se descartó la fecha.",
                campo="cosecha_sugerida",
            )
        )
        return None, None

    if siembra is not None and cosecha is None:
        # Sin fecha del agente la cosecha se deriva del ciclo investigado.
        return siembra, siembra + timedelta(days=max(ciclo, 1))

    if siembra is not None and cosecha is not None and cosecha <= siembra:
        nueva = siembra + timedelta(days=max(ciclo, 1))
        advertencias.append(
            _advertencia(
                "FECHAS_AJUSTADAS",
                f"La cosecha de {cultivo.cultivo_codigo} era anterior o igual a la "
                f"siembra: se movió a {nueva.isoformat()}.",
                campo="cosecha_sugerida",
            )
        )
        return siembra, nueva

    return siembra, cosecha


def _corregir_fuentes(
    cultivo: CultivoRecomendado,
    total_fuentes: int,
    advertencias: list[Advertencia],
    avisado: list[bool],
) -> list[int]:
    validos = sorted({indice for indice in cultivo.fuente_ids if 1 <= indice <= total_fuentes})
    if validos:
        return validos
    if total_fuentes == 0:
        if not avisado[0]:
            advertencias.append(
                _advertencia(
                    "FUENTES_INCOMPLETAS",
                    "La corrida no recuperó fuentes: la recomendación queda sin respaldo.",
                    campo="fuentes",
                )
            )
            avisado[0] = True
        return []
    return list(range(1, total_fuentes + 1))


def _corregir_sistema(
    sistema: SistemaRecomendado, advertencias: list[Advertencia]
) -> SistemaRecomendado:
    cambios: list[str] = []

    tipo = sistema.tipo if sistema.tipo in TIPOS_SISTEMA else "goteo"
    if tipo != sistema.tipo:
        cambios.append(f"tipo {sistema.tipo!r} → {tipo!r}")

    caudal = _mas_cercano(float(sistema.emisor.caudal_lh), CAUDALES_LH)
    if caudal != sistema.emisor.caudal_lh:
        cambios.append(f"caudal_lh {sistema.emisor.caudal_lh:g} → {caudal:g}")

    separacion = _limitar(float(sistema.emisor.separacion_m), SEPARACION_MIN, SEPARACION_MAX)
    if separacion != sistema.emisor.separacion_m:
        cambios.append(f"separacion_m {sistema.emisor.separacion_m:g} → {separacion:g}")

    laterales = _limitar(
        float(sistema.separacion_laterales_m), LATERALES_MIN, LATERALES_MAX
    )
    if laterales != sistema.separacion_laterales_m:
        cambios.append(
            f"separacion_laterales_m {sistema.separacion_laterales_m:g} → {laterales:g}"
        )

    bomba = _mas_cercano(float(sistema.bomba_hp), BOMBAS_HP)
    if bomba != sistema.bomba_hp:
        cambios.append(f"bomba_hp {sistema.bomba_hp:g} → {bomba:g}")

    sectores = int(_limitar(sistema.num_sectores, SECTORES_MIN, SECTORES_MAX))
    if sectores != sistema.num_sectores:
        cambios.append(f"num_sectores {sistema.num_sectores} → {sectores}")

    tanque = sistema.tanque_l
    if tanque is not None and tanque > TANQUE_MAX_L:
        cambios.append(f"tanque_l {tanque:g} → {TANQUE_MAX_L}")
        tanque = float(TANQUE_MAX_L)

    if cambios:
        advertencias.append(
            _advertencia(
                "RIEGO_AJUSTADO",
                "El backend ajustó el riego a los valores admitidos: "
                + ", ".join(cambios)
                + ".",
                campo="sistema",
            )
        )

    return SistemaRecomendado(
        tipo=tipo,
        emisor=EmisorRecomendado(
            tipo="gotero", caudal_lh=caudal, separacion_m=separacion
        ),
        separacion_laterales_m=laterales,
        tanque_l=tanque,
        bomba_hp=bomba,
        num_sectores=sectores,
    )


def corregir(
    propuesta: PropuestaAgente,
    *,
    catalogo: dict[str, dict[str, Any]],
    area_m2: float,
    total_fuentes: int,
    siembra: date | None = None,
) -> PropuestaAgente:
    """Devuelve la propuesta corregida y con las advertencias acumuladas.

    ``catalogo`` está indexado por ``codigo`` y trae ``nombre``, ``color``,
    ``demanda_agua_l_m2_dia`` y ``ciclo_dias`` de la tabla de cultivos.
    """

    advertencias = list(propuesta.advertencias)
    avisado_fuentes = [False]
    cultivos: dict[str, CultivoRecomendado] = {}
    sumadas: dict[str, float] = {}

    for cultivo in propuesta.cultivos:
        codigo = normalizar(cultivo.cultivo_codigo)
        referencia = catalogo.get(codigo)
        if referencia is None:
            advertencias.append(
                _advertencia(
                    "CULTIVO_FUERA_DE_CATALOGO",
                    f"Se descartó {cultivo.cultivo_codigo!r}: no está en el catálogo activo.",
                    campo="cultivo_codigo",
                )
            )
            continue

        ciclo_catalogo = referencia.get("ciclo_dias")
        ciclo = int(cultivo.ciclo_dias or ciclo_catalogo or CICLO_POR_DEFECTO)
        ciclo = int(_limitar(ciclo, 1, 730))
        siembra_cultivo, cosecha = _corregir_fechas(
            cultivo, ciclo, advertencias, siembra
        )
        justificacion = (cultivo.justificacion or "").strip() or JUSTIFICACION_POR_DEFECTO

        if codigo in cultivos:
            sumadas[codigo] += float(cultivo.area_m2)
            continue

        cultivos[codigo] = CultivoRecomendado(
            cultivo_codigo=codigo,
            nombre=referencia["nombre"],
            color=referencia.get("color") or cultivo.color,
            area_m2=float(cultivo.area_m2),
            demanda_l_m2_dia=_corregir_demanda(
                cultivo, referencia.get("demanda_agua_l_m2_dia"), advertencias
            ),
            ciclo_dias=ciclo,
            siembra_sugerida=siembra_cultivo,
            cosecha_sugerida=cosecha,
            justificacion=justificacion[:600],
            fuente_ids=_corregir_fuentes(
                cultivo, total_fuentes, advertencias, avisado_fuentes
            ),
        )
        sumadas[codigo] = float(cultivo.area_m2)

    if not cultivos:
        raise PropuestaInvalida(
            "Ningún cultivo de la propuesta existe en el catálogo activo"
        )

    areas = [sumadas[codigo] for codigo in cultivos]
    total = sum(areas)
    escala = 1.0
    if area_m2 > 0 and abs(total - area_m2) > 0.01:
        # El reparto tiene que cubrir el terreno completo: si sobra o falta área, se
        # escala en el sentido que haga falta y se avisa.
        escala = area_m2 / total
        codigo_alerta = "AREA_AJUSTADA" if total > area_m2 else "AREA_COMPLETADA"
        advertencias.append(
            _advertencia(
                codigo_alerta,
                f"El reparto propuesto ({total:.2f} m²) "
                + ("superaba" if total > area_m2 else "no cubría")
                + f" el terreno ({area_m2:.2f} m²): se ajustó al {escala * 100:.1f}%.",
                campo="area_m2",
            )
        )

    corregidos: list[CultivoRecomendado] = []
    for cultivo, area in zip(cultivos.values(), areas, strict=True):
        ajustada = cuantizar_area(float(_dec(area) * _dec(escala)), area_m2)
        if ajustada < _dec(AREA_MINIMA_M2):
            advertencias.append(
                _advertencia(
                    "AREA_AJUSTADA",
                    f"{cultivo.cultivo_codigo} quedó con {ajustada} m²: se descartó.",
                    campo="area_m2",
                )
            )
            continue
        corregidos.append(cultivo.model_copy(update={"area_m2": float(ajustada)}))

    if not corregidos:
        raise PropuestaInvalida("Todas las áreas propuestas quedaron por debajo del mínimo")

    return PropuestaAgente(
        cultivos=corregidos,
        sistema=_corregir_sistema(propuesta.sistema, advertencias),
        advertencias=advertencias,
    )
