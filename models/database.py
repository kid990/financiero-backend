import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    Produccion (Railway)
    'host': 'switchyard.proxy.rlwy.net',
    'database': 'railway',
    'user': 'root',
    'password': 'njZTTseYcjQJUZgpAGDZFHrwkcShkzsg',
    'port': 46378
    
    # Local
    #'host': 'localhost',
    #'database': 'riesgo_financiero',
   # 'user': 'root',
   # 'password': '',
   # 'port': 3306
}

def conectar_bd():
    """Retorna una conexión activa a la base de datos MySQL."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error al conectar con MySQL: {e}")
    return None
