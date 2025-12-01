import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from models.motor import MotorCredito
from models.consultas import obtener_cliente_por_dni, login_usuario, registrar_usuario
import requests
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
import jwt
from datetime import datetime, timedelta

API_BASE_URL = "https://dniruc.apisperu.com/api/v1"
JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6ImRhdmlkY2hpcGFjb0BnbWFpbC5jb20ifQ.jm1azZgK8jI6dOuWH8NmbAD0FOPxk6Q3xOqk4Pdp4rg"
SECRET_KEY = "mi_clave_secreta"

# Categorías permitidas
CATEGORIAS_PERMITIDAS = {
    "tipo_prestamo": ["hipotecario", "personal", "vehicular"],
    "estado_credito": ["cancelado", "deudor", "nuevo", "pendiente"],
    "estado_civil": ["casado", "divorciado", "soltero", "viudo"],
    "tipo_empleo": ["desempleado", "independiente", "permanente", "temporal"],
    "vivienda": ["alquilada", "familiar", "propia"]
}

app = FastAPI(title="Sistema de Evaluación de Riesgo Financiero", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConsultaRequest(BaseModel):
    dni: str


class ValidarEdadRequest(BaseModel):
    edad: int

class ValidarCategoriaRequest(BaseModel):
    campo: str
    valor: str


class EvaluacionRequest(BaseModel):
    dni: str
    ingreso_mensual: float
    deuda_mensual: float
    puntaje_credito: int
    monto_prestamo: float
    meses: int
    tipo_prestamo: str
    estado_credito: str
    estado_civil: str
    edad: int
    tipo_empleo: str
    vivienda: str
    present_emp_since: int
    dependientes: int

    @validator('tipo_prestamo')
    def validar_tipo_prestamo(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['tipo_prestamo']:
            raise ValueError(
                f'Tipo de préstamo inválido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["tipo_prestamo"])}')
        return v

    @validator('estado_civil')
    def validar_estado_civil(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['estado_civil']:
            raise ValueError(f'Estado civil inválido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["estado_civil"])}')
        return v

    @validator('tipo_empleo')
    def validar_tipo_empleo(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['tipo_empleo']:
            raise ValueError(f'Tipo de empleo inválido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["tipo_empleo"])}')
        return v

    @validator('vivienda')
    def validar_vivienda(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['vivienda']:
            raise ValueError(f'Tipo de vivienda inválido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["vivienda"])}')
        return v

    @validator('edad')
    def validar_edad(cls, v):
        if v < 18 or v > 75:
            raise ValueError('La edad debe estar entre 18 y 75 años')
        return v

    @validator('meses')
    def validar_meses(cls, v):
        valores_permitidos = [6, 12, 18, 24, 36, 48, 60]
        if v not in valores_permitidos:
            raise ValueError(f'Plazo inválido. Opciones: {", ".join(map(str, valores_permitidos))} meses')
        return v

    @validator('present_emp_since')
    def validar_permanencia(cls, v):
        if v < 0 or v > 12:
            raise ValueError('Los años de permanencia deben estar entre 0 y 12')
        return v

    @validator('dependientes')
    def validar_dependientes(cls, v):
        if v < 0 or v > 10:
            raise ValueError('El número de dependientes debe estar entre 0 y 10')
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    nombre: str
    apellido: str
    email: str
    telefono: str
    password: str
    rol: str = "usuario"


def _consultar_api_externa(dni: str):
    try:
        response = requests.get(
            f"{API_BASE_URL}/dni/{dni}",
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            timeout=5
        )
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None


def generate_jwt_token(usuario):
    expiration = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "sub": usuario["email"],
        "exp": expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


@app.get("/categorias")
def obtener_categorias():
    """Endpoint para obtener todas las categorías permitidas"""
    return {"categorias": CATEGORIAS_PERMITIDAS}


@app.post("/validar-edad")
def validar_edad(data: ValidarEdadRequest):
    if data.edad < 18 or data.edad > 75:
        return {
            "valido": False,
            "mensaje": "Edad fuera de rango (18-75 años)"
        }
    return {
        "valido": True,
        "mensaje": "Edad válida"
    }

@app.post("/validar-categoria")
def validar_categoria(request: ValidarCategoriaRequest):
    """Valida que un valor categórico sea correcto"""
    campo = request.campo
    valor = request.valor.lower().strip()

    if campo not in CATEGORIAS_PERMITIDAS:
        raise HTTPException(status_code=400, detail=f"Campo '{campo}' no válido")

    if valor not in CATEGORIAS_PERMITIDAS[campo]:
        return {
            "valido": False,
            "mensaje": f"Valor inválido. Opciones permitidas: {', '.join(CATEGORIAS_PERMITIDAS[campo])}",
            "opciones": CATEGORIAS_PERMITIDAS[campo]
        }

    return {
        "valido": True,
        "mensaje": "Valor válido",
        "valor_normalizado": valor
    }

import random
from fastapi import HTTPException


@app.post("/consultar-cliente")
def consultar_cliente(request: ConsultaRequest):
    try:
        dni = request.dni
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"DNI recibido: {dni}")

    # VALIDACIÓN ADICIONAL DE DNI
    if not dni or len(str(dni)) != 8 or not str(dni).isdigit():
        return {
            "encontrado": False,
            "mensaje": "DNI incorrecto ingresa 8 digitos"
        }

    # Intentamos obtener los datos del cliente desde la base de datos
    cliente = obtener_cliente_por_dni(dni)
    print(f"Cliente en base de datos: {cliente}")

    if cliente:
        nombre_completo = f"{cliente['nombre']} {cliente['apellidos']}".strip()
        deuda_mensual = float(cliente.get("deuda_mensual", 0))
        puntaje_credito = int(cliente.get("score", 0))
        estado_credito = cliente.get("estado_credito", "nuevo")
        return {
            "encontrado": True,
            "nombre": nombre_completo,
            "deuda_mensual": deuda_mensual,
            "puntaje_credito": puntaje_credito,
            "estado_credito": estado_credito
        }

    # Si no se encuentra en la base de datos, consultamos la API externa
    cliente_data = _consultar_api_externa(dni)
    print(f"Cliente en API externa: {cliente_data}")

    # Verificamos si la API externa devuelve datos válidos
    if cliente_data and cliente_data.get('success', False):
        nombres = cliente_data.get('nombres', '')
        apellidoPaterno = cliente_data.get('apellidoPaterno', '')
        apellidoMaterno = cliente_data.get('apellidoMaterno', '')

        # Unimos los nombres y apellidos, asegurándonos de que no haya valores vacíos
        nombre_completo = " ".join(filter(None, [nombres, apellidoPaterno, apellidoMaterno])).strip()

        # Si el nombre completo está vacío, asignamos un valor por defecto
        if not nombre_completo:
            nombre_completo = "Cliente sin nombre"

        # Asignamos valores predeterminados para los campos restantes
        deuda_mensual = 0.0
        puntaje_credito = random.randint(650, 750)
        estado_credito = "nuevo"

        return {
            "encontrado": True,
            "nombre": nombre_completo,
            "deuda_mensual": deuda_mensual,
            "puntaje_credito": puntaje_credito,
            "estado_credito": estado_credito
        }

    # Si no se encuentra el cliente ni en la base de datos ni en la API externa, devolvemos un mensaje de error
    return {
        "encontrado": False,
        "mensaje": "DNI incorrecto ingresa otro"
    }


@app.post("/evaluar-credito")
def evaluar_credito(request: EvaluacionRequest):
    try:
        motor = MotorCredito()
        datos_cliente = request.dict()
        resultado = motor.evaluar_prestamo(datos_cliente)

        if 'error' in resultado:
            raise HTTPException(status_code=500, detail=resultado['error'])

        return {
            "califica": "SÍ" if resultado.get('califica', 0) == 1 else "NO",
            "probabilidad": resultado.get('probabilidad', 'N/A'),
            "razon": resultado.get('razon', 'N/A'),
            "monto_aprobado": resultado.get('monto_aprobado', 0),
            "plazo_meses": resultado.get('plazo_meses', 0),
            "tasa_interes_anual": resultado.get('tasa_interes_anual', 0),
            "tasa_interes_mensual": resultado.get('tasa_interes_mensual', 0),
            "cuota_mensual": resultado.get('cuota_mensual', 0),
            "total_a_pagar": resultado.get('total_a_pagar', 0)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evaluación: {str(e)}")


@app.post("/login")
def login(request: LoginRequest):
    email = request.email.strip()
    contrasena = request.password.strip()

    if not email or not contrasena:
        raise HTTPException(status_code=400, detail="Email o contraseña vacíos")

    usuario = login_usuario(email)

    if usuario:
        if bcrypt.checkpw(contrasena.encode('utf-8'), usuario["contrasena"].encode('utf-8')):
            token = generate_jwt_token(usuario)
            return {
                "message": "Login exitoso",
                "token": token,
                "usuario": {
                    "nombre": usuario["nombre"],
                    "apellido": usuario["apellido"],
                    "email": usuario["email"],
                    "rol": usuario["rol"]
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    else:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")


@app.post("/register")
def register(request: RegisterRequest):
    nombre = request.nombre.strip()
    apellido = request.apellido.strip()
    email = request.email.strip()
    telefono = request.telefono.strip()
    contrasena = request.password.strip()
    rol = request.rol.strip()

    if not nombre or not apellido or not email or not contrasena:
        raise HTTPException(status_code=400, detail="Campos requeridos vacíos")

    usuario_existente = login_usuario(email)

    if usuario_existente:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    hashed_password = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt())

    usuario_registrado = registrar_usuario(nombre, apellido, email, telefono, hashed_password, rol)

    if usuario_registrado:
        return {"message": "Usuario registrado exitosamente"}
    else:
        raise HTTPException(status_code=500, detail="Error al registrar el usuario")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)