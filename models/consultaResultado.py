from mysql.connector import Error
from models.database import conectar_bd


def crear_resultado(datos: dict):
    """Crea un nuevo resultado en la base de datos."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO resultados (solicitud_id, califica, probabilidad, monto_aprobado,
                plazo_meses, tasa_interes_anual, tasa_interes_mensual, cuota_mensual, total_a_pagar)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            datos['solicitud_id'], datos['califica'], datos['probabilidad_raw'],
            datos['monto_aprobado'], datos['plazo_meses'], datos['tasa_interes_anual'],
            datos['tasa_interes_mensual'], datos['cuota_mensual'], datos['total_a_pagar']
        ))
        connection.commit()
        return cursor.lastrowid

    except Error as e:
        print(f"Error al crear resultado: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def obtener_resultado_por_solicitud(solicitud_id: int):
    """Obtiene el resultado de una solicitud."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM resultados WHERE solicitud_id = %s"
        cursor.execute(query, (solicitud_id,))
        return cursor.fetchone()

    except Error as e:
        print(f"Error al obtener resultado: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def obtener_resultados_por_dni(dni: str):
    """Obtiene todos los resultados de un DNI."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT r.* FROM resultados r
            INNER JOIN solicitud s ON r.solicitud_id = s.id
            WHERE s.dni = %s
        """
        cursor.execute(query, (dni,))
        resultados = cursor.fetchall()
        
        return {'resultados': resultados}

    except Error as e:
        print(f"Error al obtener resultados por DNI: {e}")
        return None

    finally:
        cursor.close()
        connection.close()
