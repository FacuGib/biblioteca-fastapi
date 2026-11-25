"""
api/libros.py
-------------
Router de FastAPI con los endpoints REST de la entidad Libro.

Responsabilidad de esta capa (HTTP):
    - Definir rutas, métodos y códigos de estado.
    - Recibir la sesión de BD mediante la dependencia get_db().
    - Delegar la lógica de datos a services/libro_service.py.
    - Devolver respuestas validadas con los esquemas Pydantic.

Todas las rutas de este archivo cuelgan del prefijo /api/libros.

Endpoints:
    GET    /api/libros        → listar libros
    POST   /api/libros        → crear libro
    GET    /api/libros/{id}   → obtener libro por id
    PUT    /api/libros/{id}   → actualizar libro
    DELETE /api/libros/{id}   → eliminar libro
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import LibroCreate, LibroRead, LibroUpdate
from services.libro_service import (
    actualizar_libro,
    crear_libro,
    eliminar_libro,  # [NUEVO]
    listar_libros,
    obtener_libro_por_id,
)

# ------------------------------------------------------------------
# Definición del router
# ------------------------------------------------------------------
# prefix → todas las rutas de este router empiezan con /api/libros
# tags   → agrupa los endpoints bajo la sección "Libros" en /docs
router = APIRouter(
    prefix="/api/libros",
    tags=["Libros"],
)

# Alias reutilizable para inyectar la sesión de BD en cada endpoint.
# Equivale a escribir:  db: Session = Depends(get_db)
DbSession = Annotated[Session, Depends(get_db)]

# Alias reutilizable para el parámetro de ruta {id}.
# Valida que sea un entero >= 1 (lo comparten GET, PUT y DELETE por id).
LibroId = Annotated[int, Path(ge=1, description="Id del libro")]


# ------------------------------------------------------------------
# GET /api/libros → Listar todos los libros
# ------------------------------------------------------------------
# Se usa la ruta "" (vacía) para que la URL final sea exactamente
# /api/libros, sin barra final ni redirecciones 307.
@router.get(
    "",
    response_model=List[LibroRead],
    summary="Listar libros",
    description="Devuelve todos los libros del catálogo, ordenados por id. "
                "Si no hay registros, devuelve una lista vacía.",
)
def obtener_libros(db: DbSession):
    """Endpoint que devuelve la lista completa de libros."""
    # 1) La capa de servicios consulta la BD y devuelve modelos ORM (Libro)
    libros = listar_libros(db)

    # 2) Conversión explícita ORM → esquema de respuesta.
    #    model_validate funciona gracias a from_attributes=True en LibroRead.
    return [LibroRead.model_validate(libro) for libro in libros]


# ------------------------------------------------------------------
# POST /api/libros → Crear un libro
# ------------------------------------------------------------------
# - datos: LibroCreate → FastAPI lee el body JSON y lo valida con Pydantic.
#   Si algo es inválido (rating fuera de rango, título vacío...), responde
#   automáticamente 422 Unprocessable Content SIN ejecutar esta función.
# - status_code=201 → código estándar REST para "recurso creado".
# - response_model=LibroRead → la respuesta incluye el id generado.
@router.post(
    "",
    response_model=LibroRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear libro",
    description="Registra un nuevo libro en el catálogo. "
                "Requiere titulo y autor (no vacíos) y rating entre 1 y 5.",
)
def agregar_libro(datos: LibroCreate, db: DbSession):
    """Endpoint que crea un libro y lo devuelve con su id."""
    # 1) El servicio convierte el esquema a ORM, hace el INSERT y el commit
    nuevo_libro = crear_libro(db, datos)

    # 2) Conversión ORM → esquema de respuesta (incluye el id asignado)
    return LibroRead.model_validate(nuevo_libro)


# ------------------------------------------------------------------
# GET /api/libros/{id} → Obtener un libro por su id
# ------------------------------------------------------------------
# - {id} en la ruta es un "path parameter": se toma de la URL.
# - LibroId valida que el id sea un entero >= 1. Si llega "abc" o 0,
#   FastAPI responde 422 automáticamente.
# - Si el libro no existe, se lanza HTTPException(404).
# - responses={404: ...} documenta ese posible error en /docs.
@router.get(
    "/{id}",
    response_model=LibroRead,
    summary="Obtener libro por id",
    description="Devuelve un libro específico según su id. "
                "Responde 404 si el libro no existe.",
    responses={404: {"description": "Libro no encontrado"}},
)
def obtener_libro(id: LibroId, db: DbSession):
    """Endpoint que devuelve un libro por su id o 404 si no existe."""
    # 1) Buscar el libro en la capa de servicios (devuelve Libro o None)
    libro = obtener_libro_por_id(db, id)

    # 2) Si no existe, cortar la ejecución con un error HTTP 404
    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Libro con id {id} no encontrado",
        )

    # 3) Conversión ORM → esquema de respuesta
    return LibroRead.model_validate(libro)


# ------------------------------------------------------------------
# PUT /api/libros/{id} → Actualizar un libro
# ------------------------------------------------------------------
# - id: viene de la URL (path parameter), validado con LibroId.
# - datos: LibroUpdate → body JSON con los campos a modificar.
#   Todos son opcionales, pero debe venir al menos uno y ninguno en null.
#   Si el body es inválido, FastAPI responde 422 sin ejecutar la función.
# - Si el libro no existe → 404.
# - Si existe → 200 OK con el libro YA actualizado.
@router.put(
    "/{id}",
    response_model=LibroRead,
    summary="Actualizar libro",
    description="Modifica un libro existente. Solo se actualizan los campos "
                "enviados en el body (titulo, autor y/o rating). "
                "Responde 404 si el libro no existe.",
    responses={404: {"description": "Libro no encontrado"}},
)
def modificar_libro(id: LibroId, datos: LibroUpdate, db: DbSession):
    """Endpoint que actualiza un libro y devuelve su versión actualizada."""
    # 1) El servicio busca el libro, aplica los cambios y hace el commit.
    #    Devuelve el Libro actualizado o None si no existe.
    libro_actualizado = actualizar_libro(db, id, datos)

    # 2) Si no existe, responder 404
    if libro_actualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Libro con id {id} no encontrado",
        )

    # 3) Devolver el recurso actualizado (ORM → esquema de respuesta)
    return LibroRead.model_validate(libro_actualizado)


# [NUEVO]
# ------------------------------------------------------------------
# DELETE /api/libros/{id} → Eliminar un libro
# ------------------------------------------------------------------
# - id: viene de la URL, validado con LibroId.
# - status_code=204 → "No Content": la operación fue exitosa y la
#   respuesta NO tiene cuerpo. FastAPI omite el body automáticamente.
# - Si el libro no existe → 404 con mensaje.
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar libro",
    description="Elimina definitivamente un libro del catálogo. "
                "Responde 204 sin contenido si se eliminó, o 404 si no existe.",
    responses={404: {"description": "Libro no encontrado"}},
)
def borrar_libro(id: LibroId, db: DbSession):
    """Endpoint que elimina un libro por su id."""
    # 1) El servicio busca y elimina el libro. Devuelve True o False.
    eliminado = eliminar_libro(db, id)

    # 2) Si no existía, responder 404
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Libro con id {id} no encontrado",
        )

    # 3) Éxito: no se devuelve nada (204 No Content)
    return None