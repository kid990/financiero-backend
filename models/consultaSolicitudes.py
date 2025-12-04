from mysql.connector import Error
from models.database import conectar_bd


def crear_solicitud(datos: dict):
    """Crea una nueva solicitud en la base de datos."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO solicitud (dni, nombre, apellidos, edad, ingreso_mensual, deuda_mensual,
                puntaje_credito, monto_prestamo, meses, present_emp_since, dependientes,
                tipo_prestamo, estado_credito, estado_civil, tipo_empleo, vivienda, estado_solicitud)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            datos['dni'], datos['nombre'], datos['apellidos'], datos['edad'],
            datos['ingreso_mensual'], datos['deuda_mensual'], datos['puntaje_credito'],
            datos['monto_prestamo'], datos.get('meses', 12), datos['present_emp_since'],
            datos['dependientes'], datos['tipo_prestamo'], datos['estado_credito'],
            datos['estado_civil'], datos['tipo_empleo'], datos['vivienda'],
            datos.get('estado_solicitud', 'pendiente')
        ))
        connection.commit()
        return cursor.lastrowid

    except Error as e:
        print(f"Error al crear solicitud: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def obtener_solicitud_por_id(solicitud_id: int):
    """Obtiene una solicitud por su ID."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM solicitud WHERE id = %s"
        cursor.execute(query, (solicitud_id,))
        return cursor.fetchone()

    except Error as e:
        print(f"Error al obtener solicitud: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def obtener_solicitudes_por_dni(dni: str, page: int = 1, limit: int = 10):
    """Obtiene solicitudes de un DNI con paginacion."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        
        # Contar total
        cursor.execute("SELECT COUNT(*) as total FROM solicitud WHERE dni = %s", (dni,))
        total = cursor.fetchone()['total']
        
        # Obtener paginado
        offset = (page - 1) * limit
        query = """
            SELECT * FROM solicitud 
            WHERE dni = %s 
            ORDER BY fecha_solicitud DESC 
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (dni, limit, offset))
        solicitudes = cursor.fetchall()
        
        return {
            'solicitudes': solicitudes,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }

    except Error as e:
        print(f"Error al obtener solicitudes: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def obtener_estadisticas_solicitudes():
    """Obtiene estadisticas de solicitudes."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN estado_solicitud = 'pendiente' THEN 1 ELSE 0 END) as pendientes,
                SUM(CASE WHEN estado_solicitud = 'aceptada' THEN 1 ELSE 0 END) as aprobadas,
                SUM(CASE WHEN estado_solicitud = 'rechazada' THEN 1 ELSE 0 END) as rechazadas
            FROM solicitud
        """
        cursor.execute(query)
        return cursor.fetchone()

    except Error as e:
        print(f"Error al obtener estadisticas: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def actualizar_estado_solicitud(solicitud_id: int, estado: str):
    """Actualiza el estado de una solicitud."""
    connection = conectar_bd()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        query = "UPDATE solicitud SET estado_solicitud = %s WHERE id = %s"
        cursor.execute(query, (estado, solicitud_id))
        connection.commit()
        return cursor.rowcount > 0

    except Error as e:
        print(f"Error al actualizar solicitud: {e}")
        return False

    finally:
        cursor.close()
        connection.close()


def editar_solicitud(solicitud_id: int, datos: dict):
    """Edita una solicitud solo si esta pendiente."""
    connection = conectar_bd()
    if not connection:
        return {'error': 'Error de conexion'}

    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT estado_solicitud FROM solicitud WHERE id = %s", (solicitud_id,))
        solicitud = cursor.fetchone()
        
        if not solicitud:
            return {'error': 'Solicitud no encontrada'}
        
        if solicitud['estado_solicitud'] != 'pendiente':
            return {'error': 'Solo se pueden editar solicitudes pendientes'}

        query = """
            UPDATE solicitud SET 
                dni = %s, nombre = %s, apellidos = %s, edad = %s, ingreso_mensual = %s,
                deuda_mensual = %s, puntaje_credito = %s, monto_prestamo = %s, meses = %s,
                present_emp_since = %s, dependientes = %s, tipo_prestamo = %s, estado_credito = %s,
                estado_civil = %s, tipo_empleo = %s, vivienda = %s
            WHERE id = %s
        """
        cursor.execute(query, (
            datos['dni'], datos['nombre'], datos['apellidos'], datos['edad'],
            datos['ingreso_mensual'], datos['deuda_mensual'], datos['puntaje_credito'],
            datos['monto_prestamo'], datos.get('meses', 12), datos['present_emp_since'],
            datos['dependientes'], datos['tipo_prestamo'], datos['estado_credito'],
            datos['estado_civil'], datos['tipo_empleo'], datos['vivienda'], solicitud_id
        ))
        connection.commit()
        return {'success': True}

    except Error as e:
        print(f"Error al editar solicitud: {e}")
        return {'error': str(e)}

    finally:
        cursor.close()
        connection.close()


def verificar_solicitud_pendiente(dni: str):
    """Verifica si un DNI tiene una solicitud pendiente."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT id FROM solicitud WHERE dni = %s AND estado_solicitud = 'pendiente' LIMIT 1"
        cursor.execute(query, (dni,))
        return cursor.fetchone()

    except Error as e:
        print(f"Error al verificar solicitud pendiente: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def listar_todas_solicitudes(page: int = 1, limit: int = 10, dni: str = None):
    """Lista todas las solicitudes con paginacion y filtro opcional por DNI."""
    connection = conectar_bd()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        
        # Contar total
        if dni:
            cursor.execute("SELECT COUNT(*) as total FROM solicitud WHERE dni LIKE %s", (f"%{dni}%",))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM solicitud")
        total = cursor.fetchone()['total']
        
        # Obtener paginado
        offset = (page - 1) * limit
        if dni:
            query = """
                SELECT * FROM solicitud 
                WHERE dni LIKE %s
                ORDER BY fecha_solicitud DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (f"%{dni}%", limit, offset))
        else:
            query = """
                SELECT * FROM solicitud 
                ORDER BY fecha_solicitud DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (limit, offset))
        
        solicitudes = cursor.fetchall()
        
        return {
            'solicitudes': solicitudes,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit if total > 0 else 0
        }

    except Error as e:
        print(f"Error al listar solicitudes: {e}")
        return None

    finally:
        cursor.close()
        connection.close()
