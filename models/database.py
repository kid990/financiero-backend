import mysql.connector
from mysql.connector import Error

def get_connection():
    """
    Retorna una conexión activa a la base de datos MySQL.
    """
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='riesgo_financiero',
            user='root',
            password=''  # coloca aquí tu contraseña real si aplica
        )
        return connection

    except Error as e:
        print(f"Error al conectar con MySQL: {e}")
        return None
