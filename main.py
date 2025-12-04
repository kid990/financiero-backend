import random
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
import jwt
import requests
from datetime import datetime, timedelta

from models.motor import MotorCredito
from models.consultasHistorial import obtener_cliente_por_dni
from models.consultasUsuario import login_usuario, registrar_usuario
from models.consultaSolicitudes import crear_solicitud, obtener_solicitud_por_id, obtener_solicitudes_por_dni, editar_solicitud, obtener_estadisticas_solicitudes, listar_todas_solicitudes, verificar_solicitud_pendiente
from models.consultaResultado import obtener_resultado_por_solicitud, obtener_resultados_por_dni

API_BASE_URL = "https://dniruc.apisperu.com/api/v1"
JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6ImRhdmlkY2hpcGFjb0BnbWFpbC5jb20ifQ.jm1azZgK8jI6dOuWH8NmbAD0FOPxk6Q3xOqk4Pdp4rg"
SECRET_KEY = "mi_clave_secreta"

CATEGORIAS_PERMITIDAS = {
    "tipo_prestamo": ["hipotecario", "personal", "vehicular"],
    "estado_credito": ["cancelado", "deudor", "nuevo", "pendiente"],
    "estado_civil": ["casado", "divorciado", "soltero", "viudo"],
    "tipo_empleo": ["desempleado", "independiente", "permanente", "temporal"],
    "vivienda": ["alquilada", "familiar", "propia"]
}

app = FastAPI(title="Sistema de Evaluacion de Riesgo Financiero", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://sistema-financiero-weld.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== MODELOS ====================

class ConsultaRequest(BaseModel):
    dni: str

class ValidarEdadRequest(BaseModel):
    edad: int

class ValidarCategoriaRequest(BaseModel):
    campo: str
    valor: str

class SolicitudRequest(BaseModel):
    dni: str
    nombre: str
    apellidos: str
    edad: int
    ingreso_mensual: float
    deuda_mensual: float
    puntaje_credito: int
    monto_prestamo: float
    meses: int
    present_emp_since: int
    dependientes: int
    tipo_prestamo: str
    estado_credito: str
    estado_civil: str
    tipo_empleo: str
    vivienda: str

    @validator('tipo_prestamo')
    def validar_tipo_prestamo(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['tipo_prestamo']:
            raise ValueError(f'Tipo de prestamo invalido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["tipo_prestamo"])}')
        return v

    @validator('estado_civil')
    def validar_estado_civil(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['estado_civil']:
            raise ValueError(f'Estado civil invalido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["estado_civil"])}')
        return v

    @validator('tipo_empleo')
    def validar_tipo_empleo(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['tipo_empleo']:
            raise ValueError(f'Tipo de empleo invalido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["tipo_empleo"])}')
        return v

    @validator('vivienda')
    def validar_vivienda(cls, v):
        v = v.lower().strip()
        if v not in CATEGORIAS_PERMITIDAS['vivienda']:
            raise ValueError(f'Tipo de vivienda invalido. Opciones: {", ".join(CATEGORIAS_PERMITIDAS["vivienda"])}')
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
            raise ValueError(f'Plazo invalido. Opciones: {", ".join(map(str, valores_permitidos))} meses')
        return v

    @validator('present_emp_since')
    def validar_permanencia(cls, v):
        if v < 0 or v > 12:
            raise ValueError('Los años de permanencia deben estar entre 0 y 12')
        return v

    @validator('dependientes')
    def validar_dependientes(cls, v):
        if v < 0 or v > 10:
            raise ValueError('El numero de dependientes debe estar entre 0 y 10')
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


# ==================== FUNCIONES AUXILIARES ====================

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
        "rol": usuario["rol"],
        "exp": expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


# ==================== MIDDLEWARE DE AUTENTICACION ====================

security = HTTPBearer()

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica que el token JWT sea válido."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def verificar_admin(payload: dict = Depends(verificar_token)):
    """Verifica que el usuario sea administrador."""
    if payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol de administrador")
    return payload


# ==================== ENDPOINTS VALIDACION ====================

@app.get("/categorias")
def obtener_categorias():
    return {"categorias": CATEGORIAS_PERMITIDAS}

@app.post("/validar-edad")
def validar_edad(data: ValidarEdadRequest):
    if data.edad < 18 or data.edad > 75:
        return {"valido": False, "mensaje": "Edad fuera de rango (18-75 años)"}
    return {"valido": True, "mensaje": "Edad valida"}

@app.post("/validar-categoria")
def validar_categoria(request: ValidarCategoriaRequest):
    campo = request.campo
    valor = request.valor.lower().strip()

    if campo not in CATEGORIAS_PERMITIDAS:
        raise HTTPException(status_code=400, detail=f"Campo '{campo}' no valido")

    if valor not in CATEGORIAS_PERMITIDAS[campo]:
        return {
            "valido": False,
            "mensaje": f"Valor invalido. Opciones permitidas: {', '.join(CATEGORIAS_PERMITIDAS[campo])}",
            "opciones": CATEGORIAS_PERMITIDAS[campo]
        }

    return {"valido": True, "mensaje": "Valor valido", "valor_normalizado": valor}


# ==================== ENDPOINTS CLIENTE ====================

@app.post("/consultar-cliente")
def consultar_cliente(request: ConsultaRequest, _: dict = Depends(verificar_admin)):
    dni = request.dni

    if not dni or len(str(dni)) != 8 or not str(dni).isdigit():
        return {"encontrado": False, "mensaje": "DNI incorrecto ingresa 8 digitos"}

    # Verificar si tiene solicitud pendiente
    solicitud_pendiente = verificar_solicitud_pendiente(dni)
    if solicitud_pendiente:
        return {
            "encontrado": False, 
            "tiene_pendiente": True,
            "solicitud_id": solicitud_pendiente['id'],
            "mensaje": "Este cliente ya tiene una solicitud pendiente de evaluación"
        }

    cliente = obtener_cliente_por_dni(dni)

    if cliente:
        nombre_completo = f"{cliente['nombre']} {cliente['apellidos']}".strip()
        return {
            "encontrado": True,
            "nombre": nombre_completo,
            "deuda_mensual": float(cliente.get("deuda_mensual", 0)),
            "puntaje_credito": int(cliente.get("score", 0)),
            "estado_credito": cliente.get("estado_credito", "nuevo")
        }

    cliente_data = _consultar_api_externa(dni)

    if cliente_data and cliente_data.get('success', False):
        nombres = cliente_data.get('nombres', '')
        apellidoPaterno = cliente_data.get('apellidoPaterno', '')
        apellidoMaterno = cliente_data.get('apellidoMaterno', '')
        nombre_completo = " ".join(filter(None, [nombres, apellidoPaterno, apellidoMaterno])).strip()

        if not nombre_completo:
            nombre_completo = "Cliente sin nombre"

        return {
            "encontrado": True,
            "nombre": nombre_completo,
            "deuda_mensual": 0.0,
            "puntaje_credito": random.randint(650, 750),
            "estado_credito": "nuevo"
        }

    return {"encontrado": False, "mensaje": "DNI incorrecto ingresa otro"}


# ==================== ENDPOINTS SOLICITUD ====================

@app.post("/crear-solicitud")
def crear_solicitud_endpoint(request: SolicitudRequest, _: dict = Depends(verificar_admin)):
    try:
        datos = request.dict()
        solicitud_id = crear_solicitud(datos)

        if not solicitud_id:
            raise HTTPException(status_code=500, detail="Error al crear solicitud")

        return {"mensaje": "Solicitud creada", "solicitud_id": solicitud_id}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/solicitud/{solicitud_id}")
def obtener_solicitud(solicitud_id: int, _: dict = Depends(verificar_admin)):
    solicitud = obtener_solicitud_por_id(solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud

@app.get("/solicitudes")
def listar_solicitudes(page: int = 1, limit: int = 10, dni: str = None, _: dict = Depends(verificar_admin)):
    resultado = listar_todas_solicitudes(page, limit, dni)
    if not resultado:
        return {"solicitudes": [], "total": 0, "page": 1, "limit": limit, "pages": 0}
    return resultado

@app.get("/solicitudes/{dni}")
def obtener_solicitudes(dni: str, page: int = 1, limit: int = 10, _: dict = Depends(verificar_admin)):
    resultado = obtener_solicitudes_por_dni(dni, page, limit)
    if not resultado:
        return {"solicitudes": [], "total": 0, "page": 1, "limit": limit, "pages": 0}
    return resultado

@app.get("/estadisticas")
def obtener_estadisticas(_: dict = Depends(verificar_admin)):
    stats = obtener_estadisticas_solicitudes()
    if not stats:
        return {"total": 0, "pendientes": 0, "aprobadas": 0, "rechazadas": 0}
    return stats

@app.put("/editar-solicitud/{solicitud_id}")
def editar_solicitud_endpoint(solicitud_id: int, request: SolicitudRequest, _: dict = Depends(verificar_admin)):
    try:
        datos = request.dict()
        resultado = editar_solicitud(solicitud_id, datos)

        if 'error' in resultado:
            raise HTTPException(status_code=400, detail=resultado['error'])

        return {"mensaje": "Solicitud editada correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS EVALUACION ====================

@app.post("/evaluar-solicitud/{solicitud_id}")
def evaluar_solicitud(solicitud_id: int, _: dict = Depends(verificar_admin)):
    try:
        solicitud = obtener_solicitud_por_id(solicitud_id)
        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")

        motor = MotorCredito()
        resultado = motor.evaluar_y_guardar(solicitud_id, solicitud)

        if 'error' in resultado:
            raise HTTPException(status_code=500, detail=resultado['error'])

        return {"mensaje": "Evaluacion completada", "resultado_id": resultado['resultado_id']}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en evaluacion: {str(e)}")

@app.get("/resultado/{solicitud_id}")
def obtener_resultado(solicitud_id: int, _: dict = Depends(verificar_admin)):
    resultado = obtener_resultado_por_solicitud(solicitud_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    return resultado

@app.get("/resultados/{dni}")
def obtener_resultados(dni: str, page: int = 1, limit: int = 10, _: dict = Depends(verificar_admin)):
    resultado = obtener_resultados_por_dni(dni, page, limit)
    if not resultado:
        return {"resultados": [], "total": 0, "page": 1, "limit": limit, "pages": 0}
    return resultado


# ==================== ENDPOINTS AUTENTICACION ====================

@app.post("/login")
def login(request: LoginRequest):
    email = request.email.strip()
    contrasena = request.password.strip()

    if not email or not contrasena:
        raise HTTPException(status_code=400, detail="Email o contraseña vacios")

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
        raise HTTPException(status_code=400, detail="Campos requeridos vacios")

    usuario_existente = login_usuario(email)

    if usuario_existente:
        raise HTTPException(status_code=400, detail="El email ya esta registrado")

    hashed_password = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt())
    usuario_registrado = registrar_usuario(nombre, apellido, email, telefono, hashed_password, rol)

    if usuario_registrado:
        return {"message": "Usuario registrado exitosamente"}
    else:
        raise HTTPException(status_code=500, detail="Error al registrar el usuario")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)