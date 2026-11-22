from app.models.agente import AgenteCorrida, AgenteFuente, AgenteRecomendacion
from app.models.catalogo import Cultivo, Suelo
from app.models.material_precio import MaterialPrecio
from app.models.proyecto import Proyecto, Terreno
from app.models.proyecto_cultivo import ProyectoCultivo
from app.models.riego import RedNodo, RedTramo, Sector, SectorBloque, SistemaRiego
from app.models.usuario import Usuario

# Importar todos los modelos deja ``Base.metadata`` completo para Alembic y para que
# ``Base.metadata.create_all`` de los tests cree el esquema entero.
__all__ = [
    "AgenteCorrida",
    "AgenteFuente",
    "AgenteRecomendacion",
    "Cultivo",
    "MaterialPrecio",
    "Proyecto",
    "ProyectoCultivo",
    "RedNodo",
    "RedTramo",
    "Sector",
    "SectorBloque",
    "SistemaRiego",
    "Suelo",
    "Terreno",
    "Usuario",
]
