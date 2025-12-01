import tensorflow as tf
import numpy as np
import pickle
import os
import pandas as pd
from models.consultas import obtener_cliente_por_dni
from funciones import calcular_tasa_interes_anual, calcular_cuota_mensual


class MotorCredito:
    def __init__(self):
        try:
            tf.get_logger().setLevel('ERROR')
            dir_actual = os.path.dirname(os.path.abspath(__file__))
            dir_raiz = os.path.dirname(dir_actual)

            modelo_path = os.path.join(dir_raiz, 'modelo_credito.keras')
            if not os.path.exists(modelo_path):
                raise FileNotFoundError(f"No se encontró el modelo en: {modelo_path}")
            self.modelo = tf.keras.models.load_model(modelo_path)

            escalador_path = os.path.join(dir_raiz, 'escalador.pkl')
            if not os.path.exists(escalador_path):
                raise FileNotFoundError(f"No se encontró el escalador en: {escalador_path}")
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
                    raise FileNotFoundError(f"No se encontró el codificador: {archivo_path}")
                with open(archivo_path, 'rb') as f:
                    setattr(self, atributo, pickle.load(f))

            caracteristicas_path = os.path.join(dir_raiz,'caracteristicas.pkl')
            if not os.path.exists(caracteristicas_path):
                raise FileNotFoundError(f"No se encontraron las características en: {caracteristicas_path}")

            with open(caracteristicas_path, 'rb') as f:
                self.caracteristicas = pickle.load(f)

            print("Motor de crédito inicializado correctamente")
            print(f"Características cargadas: {len(self.caracteristicas)}")

        except Exception as e:
            print(f"Error al inicializar el motor: {e}")
            raise

    def _codificar_valor(self, encoder, valor, default=0):
        try:
            valor_str = str(valor).lower().strip()
            if valor_str in encoder.classes_:
                return encoder.transform([valor_str])[0]
            else:
                print(f"Valor '{valor}' no encontrado en encoder. Usando default: {default}")
                return default
        except Exception as e:
            print(f"Error codificando '{valor}': {e}. Usando default: {default}")
            return default

    def evaluar_prestamo(self, datos_cliente):
        try:
            from decimal import Decimal

            datos_cliente = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in datos_cliente.items()
            }

            print("\n" + "=" * 70)
            print("EVALUACIÓN PASO 2: ANÁLISIS CON INTELIGENCIA ARTIFICIAL")
            print("=" * 70)

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
                    raise ValueError(f"Característica faltante: {feature}")

            df = pd.DataFrame([datos_modelo])[self.caracteristicas]
            print(f"Datos preparados para IA: {len(self.caracteristicas)} características")

            df_norm = self.scaler.transform(df)
            probabilidad = float(self.modelo.predict(df_norm, verbose=0)[0][0])
            califica_ia = probabilidad > 0.5

            print(f"Probabilidad de Aprobación (IA): {probabilidad * 100:.2f}%")
            print(f"Umbral de Decisión: 50.00%")
            print(f"Decisión IA: {'APROBAR' if califica_ia else 'RECHAZAR'}")

            if califica_ia:
                tasa_anual_pct = calcular_tasa_interes_anual(datos_cliente)
                tasa_mensual_pct = round(tasa_anual_pct / 12.0, 2)
                plazo_meses = datos_cliente.get('meses', 12)
                cuota_mensual = calcular_cuota_mensual(
                    datos_cliente['monto_prestamo'],
                    plazo_meses,
                    tasa_anual_pct
                )
                total_a_pagar = round(cuota_mensual * plazo_meses, 2)

                print("\n" + "=" * 70)
                print("CONDICIONES DEL PRÉSTAMO APROBADO")
                print("=" * 70)
                print(f"Monto Aprobado: S/ {datos_cliente['monto_prestamo']:,.2f}")
                print(f"Plazo: {plazo_meses} meses")
                print(f"Tasa de Interés Anual: {tasa_anual_pct}%")
                print(f"Tasa de Interés Mensual: {tasa_mensual_pct}%")
                print(f"Cuota Mensual: S/ {cuota_mensual:,.2f}")
                print(f"Total a Pagar: S/ {total_a_pagar:,.2f}")
                print("=" * 70)

                if probabilidad > 0.80:
                    razon = "Excelente perfil crediticio"
                elif probabilidad > 0.60:
                    razon = "Buen perfil crediticio"
                else:
                    razon = "Perfil crediticio aceptable"
            else:
                tasa_anual_pct = 0
                tasa_mensual_pct = 0
                cuota_mensual = 0
                total_a_pagar = 0

                if probabilidad < 0.30:
                    razon = "Perfil de alto riesgo"
                else:
                    razon = "Perfil no óptimo para el monto solicitado"

            print("\n" + "=" * 70)
            print(f"{'DECISIÓN FINAL: APROBADO' if califica_ia else 'DECISIÓN FINAL: RECHAZADO'}")
            print("=" * 70)

            return {
                'califica': int(califica_ia),
                'probabilidad': f"{probabilidad * 100:.2f}%",
                'probabilidad_raw': probabilidad,
                'monto_aprobado': datos_cliente['monto_prestamo'] if califica_ia else 0,
                'plazo_meses': datos_cliente.get('meses', 12) if califica_ia else 0,
                'tasa_interes_anual': tasa_anual_pct,
                'tasa_interes_mensual': tasa_mensual_pct,
                'cuota_mensual': cuota_mensual,
                'total_a_pagar': total_a_pagar,
                'razon': f"{razon} - Modelo IA: {probabilidad * 100:.1f}% de confianza",
                'regla_aplicada': 'Inteligencia Artificial (Post-Validación Básica)',
                'cumple_reglas_basicas': True,
                'caracteristicas_utilizadas': len(self.caracteristicas),
            }

        except Exception as e:
            print(f"Error durante la evaluación: {e}")
            import traceback
            traceback.print_exc()
            return {
                'error': str(e),
                'califica': 0,
                'probabilidad': "0.00%",
                'monto_aprobado': 0,
                'tasa_interes_anual': 0,
                'tasa_interes_mensual': 0,
                'cuota_mensual': 0,
                'total_a_pagar': 0
            }