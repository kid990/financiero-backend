from mysql.connector import Error
import bcrypt
from models.database import conectar_bd


def login_usuario(email: str):
    """Verifica si el usuario existe y devuelve sus datos si es encontrado."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT id, nombre, apellido, email, rol, contrasena
            FROM usuarios
            WHERE email = %s
        """
        cursor.execute(query, (email,))
        usuario = cursor.fetchone()
        return usuario

    except Error as e:
        print(f"Error al conectar con MySQL: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def registrar_usuario(nombre: str, apellido: str, email: str, telefono: str, contrasena: str, rol: str):
    """Registra un nuevo usuario en la base de datos si no existe ya."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)

        query_check_email = "SELECT email FROM usuarios WHERE email = %s"
        cursor.execute(query_check_email, (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return None

        query_insert = """
            INSERT INTO usuarios (nombre, apellido, email, telefono, contrasena, rol)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_insert, (nombre, apellido, email, telefono, contrasena, rol))
        connection.commit()
        return True

    except Error as e:
        print(f"Error al registrar el usuario: {e}")
        return None

    finally:
        cursor.close()
        connection.close()
