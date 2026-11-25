from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# [NUEVO] Importar la Base declarativa y registrar todos los modelos.
# Importar el paquete `models` ejecuta models/__init__.py, que importa Libro.
# Así la tabla "libros" queda registrada en Base.metadata y Alembic puede detectarla.
from database import Base, engine  # [MODIFICADO] también importamos el engine
import models  # noqa: F401  # [NUEVO]

# Objeto de configuración de Alembic: da acceso a los valores de alembic.ini
config = context.config

# [NUEVO] Tomar la URL de la BD desde database.py (que lee el .env),
# así la contraseña no queda escrita en alembic.ini.
# Los "%" se duplican porque alembic.ini los interpreta como variables.
config.set_main_option(
    "sqlalchemy.url",
    engine.url.render_as_string(hide_password=False).replace("%", "%%"),
)
# Configura el logging de Python según la sección [loggers] de alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos: Alembic la compara con la BD real
# para autogenerar las migraciones.
target_metadata = Base.metadata  # [MODIFICADO] antes: target_metadata = None


def run_migrations_offline() -> None:
    """
    Ejecuta migraciones en modo 'offline'.

    No se conecta a la BD: solo genera el SQL a partir de la URL.
    Útil para revisar o exportar el script SQL (alembic upgrade head --sql).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta migraciones en modo 'online'.

    Crea un engine con la URL de alembic.ini, abre una conexión real
    y aplica las migraciones dentro de una transacción.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# Alembic decide el modo según cómo se invoque el comando
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()