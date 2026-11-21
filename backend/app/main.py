from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    agente_corrida,
    agente_fuente,
    agente_recomendacion,
    auth,
    cultivo,
    proyecto,
    proyecto_cultivo,
    red_nodo,
    red_tramo,
    resultado,
    sector,
    sector_bloque,
    sistema_riego,
    suelo,
    terreno,
    usuario,
)

app = FastAPI(title="AgroPlan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(usuario.router)
app.include_router(cultivo.router)
app.include_router(suelo.router)
app.include_router(proyecto.router)
app.include_router(terreno.router)
app.include_router(proyecto_cultivo.router)
app.include_router(sistema_riego.router)
app.include_router(sector.router)
app.include_router(sector_bloque.router)
app.include_router(red_tramo.router)
app.include_router(red_nodo.router)
app.include_router(agente_corrida.router)
app.include_router(agente_fuente.router)
app.include_router(agente_recomendacion.router)
app.include_router(resultado.router)


@app.get("/")
def read_root():
    return {"status": "ok"}
