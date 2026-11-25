"""
models/__init__.py
------------------
Convierte la carpeta `models` en un paquete de Python y expone sus modelos.

Gracias a este archivo se puede importar así:
    from models import Libro
en lugar de:
    from models.libro import Libro

Además, al importar el paquete `models` se registran todos los modelos
en Base.metadata (necesario para que Alembic detecte las tablas).
Cada vez que agregues un modelo nuevo, impórtalo aquí.
"""

from models.libro import Libro

# Lista pública de lo que exporta el paquete
__all__ = ["Libro"]