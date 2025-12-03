import tensorflow as tf
import pickle
import os
import pandas as pd
from decimal import Decimal
from funciones import calcular_tasa_interes_anual, calcular_cuota_mensual
from models.consultaResultado import crear_resultado
from models.consultaSolicitudes import actualizar_estado_solicitud


class MotorCredito:
    def __init__(self):
        try:
            tf.get_logger().setLevel('ERROR')
            dir_actual = os.path.dirname(os.path.abspath(__file__))
            dir_raiz = os.path.dirname(dir_actual)

            modelo_path = os.path.join(dir_raiz, 'modelo_credito.keras')
            if not os.path.exists(modelo_path):
                raise FileNotFoundError(f"No se encontro el modelo en: {modelo_path}")
            self.modelo = tf.keras.models.load_model(modelo_path)

            escalador_path = os.path.join(dir_raiz, 'escalador.pkl')
            if not os.path.exists(escalador_path):
                raise FileNotFoundError(f"No se encontro el escalador en: {escalador_path}")
            with open(escalador_path, 'rb') as f:
                self.scaler = pickle.load(f)

            codificadores = [
                ('codificador_tipo_prestamo.pkl', 'le_tipo_prestamo'),
                ('codificador_estado_credito.pkl', 'le_estado_credito'),
                ('codificador_estado_civil.pkl', 'le_estado_civil'),
                ('codificador_tipo_empleo.pkl', 'le_tipo_empleo'),
                ('codificador_vivienda.pkl', 'le_vivienda')
            ]

            for archivo, atributo in codificadores:
                archivo_path = os.path.join(dir_raiz, archivo)
                if not os.path.exists(archivo_path):
                    raise FileNotFoundError(f"No se encontro el codificador: {archivo_path}")
                with open(archivo_path, 'rb') as f:
                    setattr(self, atributo, pickle.load(f))

            caracteristicas_path = os.path.join(dir_raiz, 'caracteristicas.pkl')
            if not os.path.exists(caracteristicas_path):
                raise FileNotFoundError(f"No se encontraron las caracteristicas en: {caracteristicas_path}")

            with open(caracteristicas_path, 'rb') as f:
                self.caracteristicas = pickle.load(f)

        except Exception as e:
            print(f"Error al inicializar el motor: {e}")
            raise

    def _codificar_valor(self, encoder, valor, default=0):
        try:
            valor_str = str(valor).lower().strip()
            if valor_str in encoder.classes_:
                return encoder.transform([valor_str])[0]
            else:
                return default
        except Exception:
            return default

    def evaluar_y_guardar(self, solicitud_id, datos_cliente):
        try:
            datos_cliente = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in datos_cliente.items()
            }

            tipo_prestamo_cod = self._codificar_valor(self.le_tipo_prestamo, datos_cliente['tipo_prestamo'])
            estado_credito_cod = self._codificar_valor(self.le_estado_credito, datos_cliente['estado_credito'])
            estado_civil_cod = self._codificar_valor(self.le_estado_civil, datos_cliente['estado_civil'])
            tipo_empleo_cod = self._codificar_valor(self.le_tipo_empleo, datos_cliente['tipo_empleo'])
            vivienda_cod = self._codificar_valor(self.le_vivienda, datos_cliente['vivienda'])

            datos_modelo = {
                'edad': datos_cliente['edad'],
                'ingreso_mensual': datos_cliente['ingreso_mensual'],
                'deuda_mensual': datos_cliente['deuda_mensual'],
                'puntaje_credito': datos_cliente['puntaje_credito'],
                'monto_prestamo': datos_cliente['monto_prestamo'],
                'meses': datos_cliente.get('meses', 12),
                'present_emp_since': datos_cliente['present_emp_since'],
                'dependientes': datos_cliente['dependientes'],
                'tipo_prestamo_encoded': tipo_prestamo_cod,
                'estado_credito_encoded': estado_credito_cod,
                'estado_civil_encoded': estado_civil_cod,
                'tipo_empleo_encoded': tipo_empleo_cod,
                'vivienda_encoded': vivienda_cod,
            }

            for feature in self.caracteristicas:
                if feature not in datos_modelo:
                    raise ValueError(f"Caracteristica faltante: {feature}")

            df = pd.DataFrame([datos_modelo])[self.caracteristicas]
            df_norm = self.scaler.transform(df)
            probabilidad = float(self.modelo.predict(df_norm, verbose=0)[0][0])
            califica = probabilidad > 0.5

            if califica:
                tasa_anual = calcular_tasa_interes_anual(datos_cliente)
                tasa_mensual = round(tasa_anual / 12.0, 2)
                plazo_meses = datos_cliente.get('meses', 12)
                cuota_mensual = calcular_cuota_mensual(
                    datos_cliente['monto_prestamo'],
                    plazo_meses,
                    tasa_anual
                )
                total_a_pagar = round(cuota_mensual * plazo_meses, 2)
                monto_aprobado = datos_cliente['monto_prestamo']
            else:
                tasa_anual = 0
                tasa_mensual = 0
                plazo_meses = 0
                cuota_mensual = 0
                total_a_pagar = 0
                monto_aprobado = 0

            resultado = {
                'solicitud_id': solicitud_id,
                'califica': int(califica),
                'probabilidad_raw': probabilidad,
                'monto_aprobado': monto_aprobado,
                'plazo_meses': plazo_meses,
                'tasa_interes_anual': tasa_anual,
                'tasa_interes_mensual': tasa_mensual,
                'cuota_mensual': cuota_mensual,
                'total_a_pagar': total_a_pagar
            }

            resultado_id = crear_resultado(resultado)
            if not resultado_id:
                return {'error': 'Error al guardar resultado'}

            estado = "aceptada" if califica else "rechazada"
            actualizar_estado_solicitud(solicitud_id, estado)

            return {'resultado_id': resultado_id}

        except Exception as e:
            return {'error': str(e)}