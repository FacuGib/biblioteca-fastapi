"""
models/libro.py
---------------
Modelo ORM de SQLAlchemy que representa la tabla `libros` en MySQL.

Cada instancia de la clase Libro equivale a una fila de la tabla.
Alembic usará este modelo (a través de Base.metadata) para generar
la migración que crea la tabla.
"""

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Libro(Base):
    """Representa un libro del catálogo personal."""

    # ------------------------------------------------------------------
    # Nombre de la tabla en la base de datos
    # ------------------------------------------------------------------
    __tablename__ = "libros"

    # ------------------------------------------------------------------
    # Restricciones a nivel de tabla
    # ------------------------------------------------------------------
    # CHECK en MySQL (8.0.16+): la propia base de datos rechaza
    # cualquier rating fuera del rango 1–5, aunque alguien inserte
    # datos sin pasar por la API (por ejemplo, desde Workbench).
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_libros_rating_rango"),
    )

    # ------------------------------------------------------------------
    # Columnas
    # ------------------------------------------------------------------

    # id → llave primaria entera y autoincremental.
    # MySQL asigna el valor automáticamente al insertar (AUTO_INCREMENT).
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # titulo → texto obligatorio (NOT NULL), máximo 150 caracteres.
    titulo: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # autor → texto obligatorio (NOT NULL), máximo 100 caracteres.
    autor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # rating → entero obligatorio con valor entre 1 y 5
    # (controlado por el CheckConstraint de arriba).
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Representación legible del objeto (útil para depurar)
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Libro id={self.id} titulo='{self.titulo}' "
            f"autor='{self.autor}' rating={self.rating}>"
        )