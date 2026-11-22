"""Informe descargable del paso 4 (S8): armado del documento y render a PDF.

El informe no calcula nada: consume ``ResultadoProyectoOut`` (lo que decidió el
agente y lo que grabó el motor) y lo ordena en secciones con las cifras reales. El
render con ReportLab es Python puro: no descarga imágenes ni consulta nada externo,
así el PDF se puede generar sin red.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas.agente import ResultadoProyectoOut
from app.schemas.proyecto import TerrenoOut
from app.services.agente import AgenteServiceError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.proyecto import Proyecto

MARCA_AGUA = "Estimación preliminar"

# Claves del cuerpo ``incluir`` del contrato: el cliente puede pedir un subconjunto.
# ``plano`` figura en el ejemplo del contrato (docs/flujo-sistema-agroplan.md) pero este
# informe no dibuja geometría, así que se rechaza con un mensaje claro en vez de
# devolver un PDF casi vacío como si la sección existiera.
_CLAVE_POR_SECCION = {
    "Datos del terreno": "terreno",
    "Zonificación": "zonificacion",
    "Tecnología y cabezal": "tecnologia",
    "Balance hidráulico": "agua",
    "Cómputo de materiales": "computo",
    "Calendario": "calendario",
    "Recomendaciones": "recomendaciones",
    "Fuentes consultadas": "fuentes",
    "Advertencias": "advertencias",
}

CLAVES_SOPORTADAS = frozenset(_CLAVE_POR_SECCION.values())
CLAVES_PENDIENTES = frozenset({"plano"})


@dataclass(frozen=True)
class SeccionInforme:
    """Una sección del informe ya compuesta, lista para renderizar."""

    titulo: str
    lineas: list[str] = field(default_factory=list)

    @property
    def clave(self) -> str:
        return _CLAVE_POR_SECCION.get(self.titulo, self.titulo.lower())


@dataclass(frozen=True)
class DocumentoInforme:
    """Estructura del informe, independiente del motor de render.

    El test la inspecciona directamente: así se comprueba que las secciones y las
    cifras son las del resultado sin parsear el PDF.
    """

    titulo: str
    fecha: date
    secciones: list[SeccionInforme]
    marca_agua: str = MARCA_AGUA


def _texto(valor) -> str:
    """Un dato ausente se informa como "no informado", nunca como cero (S10)."""

    if valor is None or valor == "":
        return "no informado"
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, float):
        return f"{valor:g}"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def _con_unidad(valor, unidad: str) -> str:
    if valor is None or valor == "":
        return "no informado"
    return f"{_texto(valor)} {unidad}"


def _seccion_terreno(terreno: TerrenoOut) -> SeccionInforme:
    return SeccionInforme(
        "Datos del terreno",
        [
            f"Parcela: {_texto(terreno.nombre_parcela)}",
            (
                f"Área: {_con_unidad(terreno.area_m2, 'm²')} · "
                f"Perímetro: {_con_unidad(terreno.perimetro_m, 'm')} · "
                f"Lados: {_texto(terreno.lados)}"
            ),
            (
                f"Suelo: {_texto(terreno.suelo_codigo)} · "
                f"Pendiente: {_con_unidad(terreno.pendiente_pct, '%')}"
            ),
            (
                f"Fuente de agua: {_texto(terreno.fuente_agua.value)} · "
                f"Caudal efectivo: {_con_unidad(terreno.caudal_efectivo_m3h, 'm³/h')}"
            ),
            (
                "Profundidad del nivel dinámico: "
                f"{_con_unidad(terreno.profundidad_nivel_dinamico_m, 'm')}"
            ),
        ],
    )


def _seccion_zonificacion(resultado: ResultadoProyectoOut) -> SeccionInforme:
    bloques = resultado.diseno.bloques
    if not bloques:
        return SeccionInforme("Zonificación", ["Sin bloques de cultivo informados."])

    lineas = []
    for bloque in bloques:
        nombre = bloque.nombre or bloque.cultivo_codigo
        porcentaje = (
            "no informado"
            if bloque.porcentaje is None
            else f"{bloque.porcentaje:g} %"
        )
        lineas.append(
            f"{nombre} ({bloque.cultivo_codigo}): {porcentaje} del terreno · "
            f"{_con_unidad(bloque.area_m2, 'm²')} · "
            f"ciclo: {_con_unidad(bloque.ciclo_dias, 'días')} · "
            f"siembra: {_texto(bloque.siembra)} · "
            f"cosecha: {_texto(bloque.cosecha)}"
        )
    return SeccionInforme("Zonificación", lineas)


def _seccion_tecnologia(resultado: ResultadoProyectoOut) -> SeccionInforme:
    sistema = resultado.diseno.sistema
    emisor = sistema.emisor
    return SeccionInforme(
        "Tecnología y cabezal",
        [
            f"Tipo de riego: {_texto(sistema.tipo.value)}",
            (
                f"Bomba: {_con_unidad(sistema.bomba_hp, 'HP')} · "
                f"Tanque: {_con_unidad(sistema.tanque_l, 'L')}"
            ),
            (
                f"Cabezal: emisor {_texto(emisor.tipo)} de "
                f"{_con_unidad(emisor.caudal_lh, 'L/h')} cada "
                f"{_con_unidad(emisor.separacion_m, 'm')}"
            ),
            (
                f"Diámetro principal: {_con_unidad(sistema.diametro_principal_mm, 'mm')} · "
                f"Laterales cada {_con_unidad(sistema.separacion_laterales_m, 'm')} · "
                f"Orientación: {_texto(sistema.orientacion.value)}"
            ),
            (
                f"Sectores: {_texto(sistema.num_sectores)} · "
                f"Eficiencia: {_con_unidad(resultado.diseno.eficiencia_pct, '%')}"
            ),
        ],
    )


def _seccion_balance(resultado: ResultadoProyectoOut) -> SeccionInforme:
    diseno = resultado.diseno
    cifras = diseno.cifras
    lineas = [
        f"Presión de trabajo: {_con_unidad(cifras.presion_trabajo_bar, 'bar')}",
        f"Caudal por sector: {_con_unidad(cifras.caudal_sector_m3h, 'm³/h')}",
        f"Tiempo de riego: {_con_unidad(cifras.tiempo_riego_h, 'h')}",
        f"Autonomía del tanque: {_con_unidad(cifras.autonomia_dias, 'días')}",
        f"Demanda pico: {_con_unidad(cifras.demanda_pico_l_dia, 'L/día')}",
        f"Eficiencia: {_con_unidad(diseno.eficiencia_pct, '%')}",
    ]
    for ajuste in diseno.ajustes:
        lineas.append(
            f"Ajuste del motor en {ajuste.campo}: "
            f"de {ajuste.valor_agente or 'no informado'} "
            f"a {ajuste.valor_motor or 'no informado'} — {ajuste.motivo}"
        )
    return SeccionInforme("Balance hidráulico", lineas)


def _seccion_computo(resultado: ResultadoProyectoOut) -> SeccionInforme:
    diseno = resultado.diseno
    computo = diseno.computo
    lineas = [
        (
            "Cómputo del motor: "
            f"tubería {_con_unidad(computo.tuberia_m, 'm')} · "
            f"goteros {_con_unidad(computo.goteros_u, 'u')} · "
            f"válvulas {_con_unidad(computo.valvulas_u, 'u')}"
        )
    ]
    if not diseno.materiales:
        lineas.append("El agente no informó materiales con precio.")
    for material in diseno.materiales:
        precio = (
            "sin precio"
            if material.precio_unitario_bs is None
            else f"{material.precio_unitario_bs:g} {material.moneda}"
        )
        total = (
            "sin total"
            if material.total_bs is None
            else f"{material.total_bs:g} {material.moneda}"
        )
        lineas.append(
            f"{material.rubro} — {material.descripcion}: "
            f"{_texto(material.cantidad)} {material.unidad} × {precio} = {total}"
            + (
                f" · fuente: {material.fuente_url}"
                if material.fuente_url
                else ""
            )
        )
    lineas.append(f"Total del cómputo: {_con_unidad(diseno.costo_total_bs, 'Bs')}")
    lineas.append(
        f"Presupuesto del paso 3: {_con_unidad(diseno.presupuesto_bs, 'Bs')}"
    )
    if diseno.presupuesto_excedido is None:
        comparacion = "no informada"
    elif diseno.presupuesto_excedido:
        comparacion = "el cómputo supera el presupuesto"
    else:
        comparacion = "el cómputo queda dentro del presupuesto"
    lineas.append(f"Comparación: {comparacion}")
    return SeccionInforme("Cómputo de materiales", lineas)


def _seccion_calendario(resultado: ResultadoProyectoOut) -> SeccionInforme:
    calendario = resultado.diseno.calendario
    if not calendario:
        return SeccionInforme("Calendario", ["Sin calendario informado."])
    return SeccionInforme(
        "Calendario",
        [
            f"{fila.etiqueta or fila.cultivo_codigo}: "
            f"siembra {_texto(fila.siembra)} · cosecha {_texto(fila.cosecha)}"
            for fila in calendario
        ],
    )


def _seccion_recomendaciones(resultado: ResultadoProyectoOut) -> SeccionInforme:
    recomendaciones = resultado.diseno.recomendaciones
    if not recomendaciones:
        return SeccionInforme("Recomendaciones", ["Sin recomendaciones informadas."])
    lineas = []
    for recomendacion in recomendaciones:
        linea = recomendacion.titulo
        if recomendacion.detalle:
            linea += f": {recomendacion.detalle}"
        linea += (
            f" — Justificación: {recomendacion.justificacion}"
            if recomendacion.justificacion
            else " — Justificación: no informada"
        )
        lineas.append(linea)
    return SeccionInforme("Recomendaciones", lineas)


def _seccion_fuentes(resultado: ResultadoProyectoOut) -> SeccionInforme:
    fuentes = resultado.diseno.fuentes
    if not fuentes:
        return SeccionInforme("Fuentes consultadas", ["Sin fuentes informadas."])
    return SeccionInforme(
        "Fuentes consultadas",
        [
            f"{fuente.titulo or fuente.tipo.value}: {fuente.url or 'sin URL'} "
            f"(consultada el {_texto(fuente.recuperado_en)})"
            for fuente in fuentes
        ],
    )


def _seccion_advertencias(resultado: ResultadoProyectoOut) -> SeccionInforme:
    if not resultado.advertencias:
        return SeccionInforme("Advertencias", ["Sin advertencias."])
    return SeccionInforme(
        "Advertencias",
        [
            f"{advertencia.codigo}: {advertencia.mensaje}"
            for advertencia in resultado.advertencias
        ],
    )


def _validar_incluir(incluir: list[str] | None) -> None:
    """Una clave desconocida no puede devolver un PDF casi vacío en silencio."""

    if not incluir:
        return
    desconocidas = sorted(set(incluir) - CLAVES_SOPORTADAS)
    if not desconocidas:
        return
    pendientes = sorted(set(desconocidas) & CLAVES_PENDIENTES)
    if pendientes:
        raise AgenteServiceError(
            422,
            (
                f"La sección {', '.join(pendientes)} todavía no está disponible en el "
                "informe PDF: el documento no dibuja geometría. Las secciones válidas "
                f"son: {', '.join(sorted(CLAVES_SOPORTADAS))}."
            ),
        )
    raise AgenteServiceError(
        422,
        (
            f"Sección desconocida en 'incluir': {', '.join(desconocidas)}. "
            f"Las secciones válidas son: {', '.join(sorted(CLAVES_SOPORTADAS))}."
        ),
    )


def construir_informe(
    resultado: ResultadoProyectoOut,
    terreno: TerrenoOut,
    *,
    fecha: date | None = None,
    incluir: list[str] | None = None,
) -> DocumentoInforme:
    """Arma el informe completo (S8) a partir del resultado ya calculado.

    ``incluir`` filtra secciones por las claves del contrato («agua» es el balance
    hidráulico). Sin ``incluir``, o con una lista vacía, van todas.
    """

    _validar_incluir(incluir)
    secciones = [
        _seccion_terreno(terreno),
        _seccion_zonificacion(resultado),
        _seccion_tecnologia(resultado),
        _seccion_balance(resultado),
        _seccion_computo(resultado),
        _seccion_calendario(resultado),
        _seccion_recomendaciones(resultado),
        _seccion_fuentes(resultado),
        _seccion_advertencias(resultado),
    ]
    if incluir:
        pedidas = set(incluir)
        secciones = [seccion for seccion in secciones if seccion.clave in pedidas]

    return DocumentoInforme(
        titulo=resultado.nombre,
        fecha=fecha or date.today(),
        secciones=secciones,
    )


def _marca_de_agua(canvas, _documento) -> None:
    """Marca de agua diagonal en cada página (S8)."""

    ancho, alto = A4
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 56)
    canvas.setFillColor(colors.Color(0.45, 0.45, 0.45, alpha=0.18))
    canvas.translate(ancho / 2, alto / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, MARCA_AGUA)
    canvas.restoreState()


def generar_pdf(documento: DocumentoInforme) -> bytes:
    """Renderiza el documento con ReportLab: Python puro, sin red ni imágenes."""

    buffer = BytesIO()
    titulo = ParagraphStyle(
        "TituloInforme",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1B5E20"),
    )
    subtitulo = ParagraphStyle(
        "SubtituloInforme",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#546E7A"),
    )
    encabezado = ParagraphStyle(
        "SeccionInforme",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#2E7D32"),
    )
    cuerpo = ParagraphStyle(
        "CuerpoInforme",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        spaceAfter=2,
        textColor=colors.HexColor("#263238"),
    )

    flujo = [
        Paragraph(escape(documento.titulo), titulo),
        Paragraph(
            f"Informe técnico del paso 4 · {documento.fecha.strftime('%d/%m/%Y')}",
            subtitulo,
        ),
        Paragraph(
            f"Marca de agua: {escape(documento.marca_agua)} — no apta para ejecución.",
            subtitulo,
        ),
        Spacer(1, 6),
    ]
    for seccion in documento.secciones:
        flujo.append(Paragraph(escape(seccion.titulo), encabezado))
        for linea in seccion.lineas:
            flujo.append(Paragraph(escape(linea), cuerpo))
        flujo.append(Spacer(1, 4))

    plantilla = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=documento.titulo,
        author="AgroPlan",
        # Sin compresión la marca de agua queda legible en los bytes del PDF, que es
        # lo que verifica el test de "cada página".
        pageCompression=0,
    )
    plantilla.build(flujo, onFirstPage=_marca_de_agua, onLaterPages=_marca_de_agua)
    return buffer.getvalue()


def _slug(nombre: str) -> str:
    """Nombre de archivo seguro para el ``Content-Disposition``."""

    normalizado = unicodedata.normalize("NFKD", nombre)
    ascii_ = normalizado.encode("ascii", "ignore").decode("ascii").lower()
    limpio = "".join(
        caracter if caracter.isalnum() else "-" for caracter in ascii_
    )
    slug = "-".join(parte for parte in limpio.split("-") if parte)
    return slug or "proyecto"


def informe_proyecto(
    db: Session,
    proyecto: Proyecto,
    *,
    incluir: list[str] | None = None,
) -> tuple[bytes, str]:
    """PDF del proyecto ya generado y su nombre de archivo (S8).

    ``resultado_proyecto`` es la única fuente de cifras: si la red todavía no se
    generó levanta ``AgenteServiceError`` y el endpoint responde 4xx, nunca un PDF
    vacío.
    """

    from app.services import agente as agente_service
    from app.services import terreno as terreno_service

    resultado = agente_service.resultado_proyecto(db, proyecto)
    terreno = terreno_service.obtener_terreno(db, proyecto)
    documento = construir_informe(resultado, terreno, incluir=incluir)
    return generar_pdf(documento), _slug(proyecto.nombre)
