"""
main.py
-------
Punto de entrada de la API REST "Biblioteca Personal".

Aquí se crea la instancia principal de FastAPI, se configura CORS
y se registran los routers. Uvicorn busca esta instancia (llamada `app`)
para levantar el servidor.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # [NUEVO]

from api.libros import router as libros_router

# ------------------------------------------------------------------
# Instancia principal de la aplicación
# ------------------------------------------------------------------
# `app` es el objeto central de FastAPI:
#   - Registra todas las rutas (endpoints) de la API.
#   - Recibe los routers y los middlewares (como CORS).
#   - Genera automáticamente la documentación en /docs y /redoc.
app = FastAPI(
    title="API Biblioteca Personal",
    description="Backend REST para administrar un catálogo personal de libros 📚",
    version="1.0.0",
)

# [NUEVO]
# ------------------------------------------------------------------
# Configuración de CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------
# Lista de orígenes (protocolo + dominio + puerto) autorizados a
# consumir la API desde el navegador.
# Se incluyen "localhost" y "127.0.0.1" porque para el navegador
# son orígenes DISTINTOS aunque apunten a la misma máquina.
ORIGENES_PERMITIDOS = [
    "http://localhost:4200",   # Angular (ng serve)
    "http://127.0.0.1:4200",
    "http://localhost:5173",   # React con Vite (npm run dev)
    "http://127.0.0.1:5173",
]

# El middleware intercepta cada petición y agrega las cabeceras
# Access-Control-Allow-* que el navegador necesita para permitirla.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,      # quién puede llamar a la API
    allow_credentials=True,                 # permite cookies/cabeceras de autenticación
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # métodos del CRUD + preflight
    allow_headers=["*"],                    # cualquier cabecera (Content-Type, Authorization...)
)

# ------------------------------------------------------------------
# Registro de routers
# ------------------------------------------------------------------
# include_router agrega a la app todas las rutas definidas en api/libros.py
# (con su prefijo /api/libros y su tag "Libros").
app.include_router(libros_router)


# ------------------------------------------------------------------
# Endpoint de prueba (health check)
# ------------------------------------------------------------------
# GET /
# Sirve para verificar rápidamente que la API está levantada y respondiendo.
# FastAPI convierte automáticamente el diccionario devuelto en JSON.
@app.get("/", tags=["Inicio"])
def inicio():
    """Devuelve un mensaje simple indicando que la API está funcionando."""
    return {
        "mensaje": "API Biblioteca Personal funcionando correctamente 🚀",
        "estado": "ok",
    }