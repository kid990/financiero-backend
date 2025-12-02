import mysql.connector
from mysql.connector import Error

def get_connection():
    """
    Retorna una conexión activa a la base de datos MySQL.
    """
    try:
        connection = mysql.connector.connect(
           host='switchyard.proxy.rlwy.net',
database='railway',
user='root',
password='njZTTseYcjQJUZgpAGDZFHrwkcShkzsg',
port=46378

        )
        return connection

    except Error as e:
        print(f"Error al conectar con MySQL: {e}")
        return None
