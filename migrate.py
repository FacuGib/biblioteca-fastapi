"""
migrate.py
----------
Automatiza las migraciones de Alembic con un solo comando:

    python migrate.py

Pasos que realiza:
    1. Carga las variables del archivo .env.
    2. Configura Alembic usando la URL de conexión del .env.
    3. Detecta y limpia una versión huérfana en la tabla alembic_version
       (cuando la BD apunta a una revisión cuyo archivo ya no existe).
    4. Aplica las migraciones pendientes que ya existan (upgrade head).
    5. Compara los modelos con la BD; si hay cambios, genera una revisión
       autogenerada y la aplica con upgrade head.
"""

import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ------------------------------------------------------------------
# 1) Cargar .env antes de importar la configuración de la BD
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from database import DATABASE_URL, Base, engine  # noqa: E402
import models  # noqa: F401, E402  (registra los modelos en Base.metadata)


# ------------------------------------------------------------------
# 2) Configuración de Alembic
# ------------------------------------------------------------------
def obtener_config_alembic() -> Config:
    """
    Crea el objeto Config de Alembic a partir de alembic.ini y
    sobrescribe la URL con la del .env (única fuente de verdad).
    """
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    # En archivos .ini el símbolo % es especial: se escapa como %%
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
    return cfg


# ------------------------------------------------------------------
# 3) Limpieza de versión huérfana
# ------------------------------------------------------------------
def limpiar_version_huerfana(cfg: Config) -> None:
    """
    Si la tabla alembic_version guarda una revisión que ya no existe
    en alembic/versions (por ejemplo, porque se borró el archivo),
    Alembic falla con "Can't locate revision". Aquí se elimina ese registro.
    """
    inspector = inspect(engine)
    if not inspector.has_table("alembic_version"):
        print("ℹ️  No existe la tabla alembic_version (primera migración).")
        return

    script = ScriptDirectory.from_config(cfg)

    with engine.begin() as conexion:
        versiones = [
            fila[0]
            for fila in conexion.execute(text("SELECT version_num FROM alembic_version"))
        ]

        if not versiones:
            print("ℹ️  alembic_version está vacía.")
            return

        for version in versiones:
            try:
                existe = script.get_revision(version) is not None
            except Exception:
                existe = False

            if existe:
                print(f"✅ Versión actual válida: {version}")
            else:
                conexion.execute(
                    text("DELETE FROM alembic_version WHERE version_num = :v"),
                    {"v": version},
                )
                print(f"🧹 Versión huérfana eliminada de alembic_version: {version}")


# ------------------------------------------------------------------
# 4) Detección de cambios entre modelos y BD
# ------------------------------------------------------------------
def detectar_cambios() -> list:
    """
    Compara Base.metadata (modelos) contra el esquema real de MySQL.
    Devuelve la lista de diferencias (vacía si todo está sincronizado).
    """
    with engine.connect() as conexion:
        contexto = MigrationContext.configure(conexion)
        return compare_metadata(contexto, Base.metadata)


# ------------------------------------------------------------------
# 5) Flujo principal
# ------------------------------------------------------------------
def main() -> None:
    print("🚀 Iniciando proceso de migración...\n")
    cfg = obtener_config_alembic()

    # Paso A: limpiar versiones huérfanas
    limpiar_version_huerfana(cfg)

    # Paso B: aplicar migraciones existentes que estén pendientes
    print("\n⏫ Aplicando migraciones pendientes (si las hay)...")
    command.upgrade(cfg, "head")

    # Paso C: detectar cambios en los modelos
    cambios = detectar_cambios()
    if not cambios:
        print("\n✅ La base de datos ya está sincronizada con los modelos. No hay cambios.")
        return

    print(f"\n🔍 Se detectaron {len(cambios)} cambio(s) en los modelos:")
    for cambio in cambios:
        print(f"   • {cambio[0] if isinstance(cambio, tuple) else cambio}")

    # Paso D: generar la revisión autogenerada
    mensaje = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n📝 Generando revisión: {mensaje}")
    command.revision(cfg, message=mensaje, autogenerate=True)

    # Paso E: aplicar la nueva revisión
    print("\n⏫ Aplicando upgrade head...")
    command.upgrade(cfg, "head")

    print("\n🎉 Migración completada correctamente.")


if __name__ == "__main__":
    try:
        main()
    except SQLAlchemyError as error:
        print(f"\n❌ Error de base de datos: {error}")
        sys.exit(1)
    except Exception as error:
        print(f"\n❌ Error durante la migración: {error}")
        sys.exit(1)