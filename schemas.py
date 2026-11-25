"""
schemas.py
----------
Esquemas Pydantic (v2) para validar las entradas y salidas de la API de libros.

¿Por qué varios esquemas y no uno solo?
    - LibroBase   → campos y reglas COMUNES (titulo, autor, rating).
    - LibroCreate → lo que el cliente envía para CREAR (POST). Sin id,
                    porque lo asigna MySQL.
    - LibroUpdate → lo que el cliente envía para ACTUALIZAR (PUT). Todos
                    los campos son opcionales: se modifica solo lo enviado.
    - LibroRead   → lo que la API DEVUELVE. Incluye el id.

Así cada operación expone exactamente los campos que corresponden:
el cliente nunca puede "inventar" un id al crear, y las respuestas
siempre tienen la misma estructura.

Importante: estos esquemas NO son el modelo de base de datos.
    models.Libro (SQLAlchemy) → cómo se GUARDA en MySQL.
    schemas.Libro* (Pydantic) → cómo VIAJA por HTTP (JSON).
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ------------------------------------------------------------------
# Tipos reutilizables con sus reglas de validación
# ------------------------------------------------------------------
# Annotated junta el tipo de dato con sus restricciones en un solo lugar.
# Las longitudes máximas coinciden con las columnas del modelo (150 y 100).

# Título: texto no vacío, máximo 150 caracteres
Titulo = Annotated[
    str,
    Field(min_length=1, max_length=150, description="Título del libro"),
]

# Autor: texto no vacío, máximo 100 caracteres
Autor = Annotated[
    str,
    Field(min_length=1, max_length=100, description="Autor del libro"),
]

# Rating: entero entre 1 y 5 (inclusive)
Rating = Annotated[
    int,
    Field(ge=1, le=5, description="Calificación del libro (1 a 5)"),
]

# ------------------------------------------------------------------
# Configuración común
# ------------------------------------------------------------------
# str_strip_whitespace=True elimina espacios al inicio y al final ANTES
# de validar la longitud. Así "   " queda como "" y es rechazado por
# min_length=1 (no se aceptan títulos ni autores "en blanco").
CONFIG_BASE = ConfigDict(str_strip_whitespace=True)


# ==================================================================
# LibroBase: campos y validaciones compartidas
# ==================================================================
class LibroBase(BaseModel):
    """Campos comunes de un libro, con todas sus validaciones."""

    model_config = CONFIG_BASE

    titulo: Titulo
    autor: Autor
    rating: Rating


# ==================================================================
# LibroCreate: datos de entrada para crear (POST /api/libros)
# ==================================================================
class LibroCreate(LibroBase):
    """
    Esquema para crear un libro.

    Hereda todo de LibroBase: los tres campos son OBLIGATORIOS.
    No incluye `id`, porque lo genera MySQL (AUTO_INCREMENT).
    Se mantiene como clase propia para poder agregar en el futuro
    campos exclusivos de la creación sin afectar a los demás esquemas.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"titulo": "Cien años de soledad", "autor": "Gabriel García Márquez", "rating": 5}
            ]
        },
    )


# ==================================================================
# LibroUpdate: datos de entrada para actualizar (PUT /api/libros/{id})
# ==================================================================
class LibroUpdate(BaseModel):
    """
    Esquema para actualizar un libro.

    Todos los campos son OPCIONALES: el cliente envía solo lo que quiere
    cambiar (actualización parcial). Los campos enviados se validan con
    las mismas reglas que al crear.

    Reglas adicionales:
        - Un campo enviado explícitamente como null se rechaza
          (no se puede dejar un libro sin título, autor o rating).
        - El body no puede venir vacío: debe incluir al menos un campo.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"rating": 4}]},
    )

    titulo: Titulo | None = None
    autor: Autor | None = None
    rating: Rating | None = None

    # Se ejecuta solo para los campos que el cliente ENVIÓ.
    # Los campos omitidos quedan con su valor por defecto y no pasan por aquí.
    @field_validator("titulo", "autor", "rating")
    @classmethod
    def no_permitir_nulos(cls, valor):
        """Rechaza null explícito en cualquier campo enviado."""
        if valor is None:
            raise ValueError("El campo no puede ser null; omítelo si no deseas modificarlo")
        return valor

    # Se ejecuta después de validar todos los campos.
    @model_validator(mode="after")
    def al_menos_un_campo(self):
        """Exige que el body incluya al menos un campo para actualizar."""
        if not self.model_fields_set:
            raise ValueError("Debes enviar al menos un campo: titulo, autor o rating")
        return self


# ==================================================================
# LibroRead: datos de salida (respuestas de la API)
# ==================================================================
class LibroRead(LibroBase):
    """
    Esquema de respuesta: lo que la API devuelve al cliente.

    Incluye el `id` generado por la base de datos.
    from_attributes=True permite construirlo directamente desde un
    objeto SQLAlchemy (models.Libro), leyendo sus atributos:
        LibroRead.model_validate(libro_orm)
    FastAPI usa esto automáticamente cuando declaras response_model=LibroRead.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(description="Identificador único del libro")