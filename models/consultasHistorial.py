from mysql.connector import Error
from models.database import conectar_bd


def obtener_cliente_por_dni(dni: str):
    """Devuelve los datos del cliente si existe en la BD, o None si no está."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT dni, nombre, apellidos, deuda_mensual, score, estado_credito
            FROM historial
            WHERE dni = %s
        """
        cursor.execute(query, (dni,))
        resultado = cursor.fetchone()
        return resultado

    except Error as e:
        print(f"Error al consultar cliente por DNI: {e}")
        return None

    finally:
        cursor.close()
        connection.close()
