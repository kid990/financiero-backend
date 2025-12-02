import mysql.connector
from mysql.connector import Error
import bcrypt  # Usamos bcrypt para encriptar contraseñas de forma segura.



# Función común para conectar a la base de datos
def conectar_bd():
    """Establece la conexión a la base de datos MySQL."""
    try:
        connection = mysql.connector.connect(
            host='switchyard.proxy.rlwy.net',
database='railway',
user='root',
password='njZTTseYcjQJUZgpAGDZFHrwkcShkzsg',
port=46378
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"❌ Error al conectar con MySQL: {e}")
        return None

# Función para obtener el cliente por DNI
def obtener_cliente_por_dni(dni: str):
    """Devuelve los datos del cliente si existe en la BD, o None si no está."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
                SELECT dni, nombre, apellidos, deuda_mensual, score, estado_credito
                FROM historial_crediticio_completo
                WHERE dni = %s
        """
        cursor.execute(query, (dni,))
        resultado = cursor.fetchone()
        return resultado

    except Error as e:
        print(f"❌ Error al consultar cliente por DNI: {e}")
        return None

    finally:
        cursor.close()
        connection.close()




# Función para consultar un usuario por su email y verificar su contraseña (login)
def login_usuario(email: str):
    """Verifica si el usuario existe y devuelve sus datos si es encontrado."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)

        # Consulta a la base de datos por el email
        query = """
                SELECT id, nombre, apellido,email, rol, contrasena
                FROM usuarios
                WHERE email = %s
        """
        cursor.execute(query, (email,))
        usuario = cursor.fetchone()

        if usuario:
            return usuario  # Si el usuario es encontrado, devolver los datos
        else:
            return None  # No se encontró el usuario

    except Error as e:
        print(f"❌ Error al conectar con MySQL: {e}")
        return None

    finally:
        cursor.close()
        connection.close()



## Función para registrar un nuevo usuario
def registrar_usuario(nombre: str, apellido: str, email: str, telefono: str, contrasena: str, rol: str):
    """Registra un nuevo usuario en la base de datos si no existe ya."""
    connection = conectar_bd()
    if not connection:
        return None  # En caso de error en la conexión

    try:
        cursor = connection.cursor(dictionary=True)

        # Verificar si el email ya está registrado
        query_check_email = """
                            SELECT email
                            FROM usuarios
                            WHERE email = %s
        """
        cursor.execute(query_check_email, (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return None  # El email ya está registrado

        # Insertar el nuevo usuario con la contraseña encriptada
        query_insert = """
                       INSERT INTO usuarios (nombre, apellido, email, telefono, contrasena, rol)
                       VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_insert, (nombre, apellido, email, telefono, contrasena, rol))
        connection.commit()  # Confirmamos los cambios

        return True  # Usuario registrado exitosamente

    except Error as e:
        print(f"❌ Error al registrar el usuario: {e}")
        return None  # En caso de error

    finally:
        cursor.close()
        connection.close()

