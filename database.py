"""
database.py
-----------
Configuración central de la conexión a MySQL con SQLAlchemy.

Contiene:
    - engine       → motor de conexión a la base de datos.
    - SessionLocal → fábrica de sesiones (una sesión por petición).
    - Base         → clase base de la que heredarán los modelos ORM.
    - get_db()     → dependencia de FastAPI que entrega y cierra la sesión.

También permite probar la conexión ejecutando:  python database.py
"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

# ------------------------------------------------------------------
# 1) Cargar variables de entorno desde .env
# ------------------------------------------------------------------
# Se busca el .env en la misma carpeta que este archivo, así funciona
# aunque el comando se ejecute desde otra ruta (Alembic, PyCharm, etc.).
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "biblioteca_db")

# ------------------------------------------------------------------
# 2) Construir la URL de conexión
# ------------------------------------------------------------------
# Formato: mysql+pymysql://usuario:password@host:puerto/base_de_datos
# quote_plus() escapa caracteres especiales de la contraseña (@, #, :, etc.)
# para que no rompan la URL.
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# ------------------------------------------------------------------
# 3) Crear el engine (motor de conexión)
# ------------------------------------------------------------------
# - pool_pre_ping=True: verifica que la conexión siga viva antes de usarla
#   (evita errores tipo "MySQL server has gone away").
# - echo=False: no muestra el SQL generado en consola (ponlo en True para depurar).
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

# ------------------------------------------------------------------
# 4) Fábrica de sesiones
# ------------------------------------------------------------------
# Cada llamada a SessionLocal() crea una sesión nueva para hablar con la BD.
# - autocommit=False: los cambios se confirman explícitamente con db.commit().
# - autoflush=False: evita envíos automáticos a la BD antes de tiempo.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ------------------------------------------------------------------
# 5) Clase base para los modelos ORM
# ------------------------------------------------------------------
# Todos los modelos (por ejemplo, Libro) heredarán de Base.
# Alembic usará Base.metadata para detectar las tablas.
Base = declarative_base()


# ------------------------------------------------------------------
# 6) Dependencia de FastAPI: una sesión por petición
# ------------------------------------------------------------------
def get_db():
    """
    Abre una sesión de BD para la petición actual y la cierra siempre al terminar.

    Uso en un endpoint:
        def mi_endpoint(db: Session = Depends(get_db)): ...

    `yield` entrega la sesión al endpoint; el bloque `finally` se ejecuta
    cuando la respuesta termina, incluso si hubo un error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# 7) Prueba rápida de conexión
# ------------------------------------------------------------------
# Solo se ejecuta con:  python database.py
# Abre una conexión real con MySQL (sin consultas) y muestra el resultado.
if __name__ == "__main__":
    try:
        with engine.connect():
            print("✅ Conexión exitosa a MySQL")
            print(f"   Base de datos: {DB_NAME}  |  Host: {DB_HOST}:{DB_PORT}  |  Usuario: {DB_USER}")
    except SQLAlchemyError as error:
        print("❌ Error al conectar con MySQL")
        print(f"   Detalle: {error}")