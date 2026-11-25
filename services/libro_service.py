"""
services/libro_service.py
-------------------------
Capa de servicios para la entidad Libro.

¿Por qué una capa de servicios?
    - Separa la lógica de acceso a datos de la capa HTTP (routers).
    - Los endpoints quedan cortos: reciben la petición, llaman al servicio
      y devuelven la respuesta.
    - Las funciones se pueden reutilizar (otro endpoint, un script,
      pruebas automáticas) sin depender de FastAPI.
    - Si cambia la forma de consultar la BD, solo se modifica este archivo.

Cada función recibe la sesión de BD (`db`) como parámetro. La sesión la
crea y la cierra la dependencia get_db() de database.py.
"""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import Libro
from schemas import LibroCreate, LibroUpdate


# ------------------------------------------------------------------
# Listar libros
# ------------------------------------------------------------------
def listar_libros(db: Session) -> list[Libro]:
    """
    Devuelve todos los libros registrados en la tabla `libros`.

    Parámetros:
        db: sesión activa de SQLAlchemy (inyectada desde el router).

    Retorna:
        Lista de objetos Libro ordenados por id ascendente.
        Si la tabla está vacía, devuelve una lista vacía [].
    """
    # select(Libro) equivale a: SELECT * FROM libros
    # order_by(Libro.id) asegura un orden estable en las respuestas.
    consulta = select(Libro).order_by(Libro.id)

    # db.scalars(...) ejecuta la consulta y devuelve directamente
    # objetos Libro (no tuplas). .all() los convierte en una lista.
    return list(db.scalars(consulta).all())


# ------------------------------------------------------------------
# Crear libro
# ------------------------------------------------------------------
def crear_libro(db: Session, datos: LibroCreate) -> Libro:
    """
    Crea un nuevo libro en la base de datos.

    Parámetros:
        db:    sesión activa de SQLAlchemy.
        datos: esquema LibroCreate ya validado por Pydantic
               (titulo y autor no vacíos, rating entre 1 y 5).

    Retorna:
        El objeto Libro persistido, incluyendo el `id` asignado por MySQL.

    Flujo:
        1. Pydantic → dict      : datos.model_dump()
        2. dict → modelo ORM    : Libro(**dict)
        3. db.add()             : marca el objeto para insertarlo
        4. db.commit()          : ejecuta el INSERT y confirma la transacción
        5. db.refresh()         : recarga el objeto desde la BD (obtiene el id)
    """
    # 1 y 2) Convertir el esquema Pydantic en una instancia del modelo ORM.
    #        model_dump() → {"titulo": "...", "autor": "...", "rating": 5}
    #        **dict desempaqueta las claves como argumentos: Libro(titulo=..., ...)
    nuevo_libro = Libro(**datos.model_dump())

    try:
        # 3) Agregar el objeto a la sesión (aún no se guarda en MySQL)
        db.add(nuevo_libro)

        # 4) Confirmar: aquí se ejecuta realmente el INSERT INTO libros ...
        db.commit()
    except SQLAlchemyError:
        # Si falla el INSERT (por ejemplo, se viola el CHECK del rating),
        # se deshacen los cambios para dejar la sesión en un estado limpio
        # y se relanza el error para que lo maneje la capa superior.
        db.rollback()
        raise

    # 5) Refrescar el objeto con los valores generados por la BD (el id)
    db.refresh(nuevo_libro)

    return nuevo_libro


# ------------------------------------------------------------------
# Obtener libro por id
# ------------------------------------------------------------------
def obtener_libro_por_id(db: Session, id: int) -> Libro | None:
    """
    Busca un libro por su llave primaria.

    Parámetros:
        db: sesión activa de SQLAlchemy.
        id: identificador del libro a buscar.

    Retorna:
        - El objeto Libro si existe.
        - None si no hay ningún libro con ese id.

    El servicio NO lanza errores HTTP: solo informa "no existe" con None.
    El router decide la respuesta adecuada (por ejemplo, 404 Not Found).
    """
    # db.get(Modelo, pk) es la forma más directa de buscar por llave primaria.
    # Equivale a: SELECT * FROM libros WHERE id = :id
    # Si el objeto ya está cargado en la sesión, lo devuelve sin ir a la BD.
    return db.get(Libro, id)


# ------------------------------------------------------------------
# Actualizar libro
# ------------------------------------------------------------------
def actualizar_libro(db: Session, id: int, datos: LibroUpdate) -> Libro | None:
    """
    Actualiza un libro existente con los campos recibidos.

    Implementa una actualización PARCIAL: solo se modifican los campos
    que el cliente envió en el body. Los demás conservan su valor.

    Parámetros:
        db:    sesión activa de SQLAlchemy.
        id:    identificador del libro a actualizar.
        datos: esquema LibroUpdate ya validado por Pydantic
               (campos opcionales, al menos uno presente, sin nulls).

    Retorna:
        - El objeto Libro actualizado si existe.
        - None si no hay ningún libro con ese id (el router responderá 404).

    Flujo:
        1. Localizar el libro (reutilizando obtener_libro_por_id).
        2. Si no existe → devolver None.
        3. Obtener solo los campos enviados: model_dump(exclude_unset=True).
        4. Asignar cada valor al objeto ORM con setattr().
        5. db.commit() → ejecuta el UPDATE.
        6. db.refresh() → recarga el objeto con los valores guardados.
    """
    # 1) Localizar el libro
    libro = obtener_libro_por_id(db, id)

    # 2) Caso "no encontrado": se informa con None, sin lanzar errores HTTP
    if libro is None:
        return None

    # 3) Solo los campos que el cliente envió.
    #    Ejemplo: body {"rating": 3} → {"rating": 3}
    #    (titulo y autor no aparecen, así que NO se tocan)
    cambios = datos.model_dump(exclude_unset=True)

    # 4) Aplicar cada cambio sobre el objeto ORM.
    #    setattr(libro, "rating", 3) equivale a: libro.rating = 3
    #    SQLAlchemy detecta qué atributos cambiaron y arma el UPDATE.
    for campo, valor in cambios.items():
        setattr(libro, campo, valor)

    try:
        # 5) Confirmar: aquí se ejecuta UPDATE libros SET ... WHERE id = :id
        db.commit()
    except SQLAlchemyError:
        # Si falla, se deshacen los cambios y se relanza el error
        db.rollback()
        raise

    # 6) Recargar el objeto con los valores definitivos de la BD
    db.refresh(libro)

    return libro


# [NUEVO]
# ------------------------------------------------------------------
# Eliminar libro
# ------------------------------------------------------------------
def eliminar_libro(db: Session, id: int) -> bool:
    """
    Elimina físicamente un libro de la base de datos.

    Parámetros:
        db: sesión activa de SQLAlchemy.
        id: identificador del libro a eliminar.

    Retorna:
        - True  si el libro existía y se eliminó.
        - False si no hay ningún libro con ese id (el router responderá 404).

    Flujo:
        1. Localizar el libro (reutilizando obtener_libro_por_id).
        2. Si no existe → devolver False.
        3. db.delete() → marca el objeto para borrarlo.
        4. db.commit() → ejecuta el DELETE y confirma la transacción.
    """
    # 1) Localizar el libro
    libro = obtener_libro_por_id(db, id)

    # 2) Caso "no encontrado": se informa con False, sin lanzar errores HTTP
    if libro is None:
        return False

    try:
        # 3) Marcar el objeto para eliminarlo (aún no se borra en MySQL)
        db.delete(libro)

        # 4) Confirmar: aquí se ejecuta DELETE FROM libros WHERE id = :id
        db.commit()
    except SQLAlchemyError:
        # Si falla, se deshacen los cambios y se relanza el error
        db.rollback()
        raise

    return True