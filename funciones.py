import math

def calcular_tasa_interes_anual(datos):
    tipo_prestamo   = str(datos.get('tipo_prestamo', '')).lower()
    tipo_empleo     = str(datos.get('tipo_empleo', '')).lower()
    puntaje         = int(datos.get('puntaje_credito', 600))
    monto           = float(datos.get('monto_prestamo', 10000))
    ingreso_mensual = float(datos.get('ingreso_mensual', 2000))

    if tipo_prestamo == 'personal':
        tasa_min = 20.0
        tasa_max = 80.0
    elif tipo_prestamo == 'vehicular':
        tasa_min = 10.0
        tasa_max = 30.0
    elif tipo_prestamo == 'hipotecario':
        tasa_min = 7.0
        tasa_max = 12.0
    else:
        tasa_min = 15.0
        tasa_max = 40.0

    puntaje_min = 300
    puntaje_max = 950
    puntaje_clamped = max(puntaje_min, min(puntaje_max, puntaje))
    riesgo_puntaje = 1.0 - (puntaje_clamped - puntaje_min) / (puntaje_max - puntaje_min)
    tasa_por_puntaje = tasa_min + riesgo_puntaje * (tasa_max - tasa_min)

    if tipo_empleo in ['permanente']:
        ajuste_empleo = -2.0
    elif tipo_empleo in ['independiente']:
        ajuste_empleo = -1.0
    elif tipo_empleo in ['temporal']:
        ajuste_empleo = +2.0
    else:
        ajuste_empleo = +4.0

    if monto >= 80000:
        ajuste_monto = -2.0
    elif monto >= 30000:
        ajuste_monto = -1.0
    elif monto <= 3000:
        ajuste_monto = +1.0
    else:
        ajuste_monto = 0.0

    if ingreso_mensual >= 8000:
        ajuste_ingreso = -1.5
    elif ingreso_mensual >= 4000:
        ajuste_ingreso = -0.5
    elif ingreso_mensual < 1500:
        ajuste_ingreso = +1.0
    else:
        ajuste_ingreso = 0.0

    tasa_interes_anual = tasa_por_puntaje + ajuste_empleo + ajuste_monto + ajuste_ingreso
    tasa_interes_anual = max(tasa_min, min(tasa_max, tasa_interes_anual))

    return round(tasa_interes_anual, 2)

def calcular_cuota_mensual(monto_prestamo, plazo_meses, tasa_anual_pct):
    try:
        if plazo_meses <= 0:
            return 0.0

        tasa_anual_decimal = float(tasa_anual_pct) / 100.0
        tasa_mensual = tasa_anual_decimal / 12.0

        if math.isclose(tasa_mensual, 0.0, abs_tol=1e-12):
            cuota_mensual = monto_prestamo / plazo_meses
        else:
            P = monto_prestamo
            r = tasa_mensual
            n = plazo_meses
            cuota_mensual = (P * r * (1 + r) ** n) / ((1 + r) ** n - 1)

        return round(float(cuota_mensual), 2)
    except Exception:
        return 0.0


def calcular_deuda_mensual(monto_prestamo, estado_credito, plazo, tasa_interes_anual_pct):
    try:
        if str(estado_credito).lower() != 'pendiente':
            return 0.0

        return calcular_cuota_mensual(monto_prestamo, plazo, tasa_interes_anual_pct)
    except Exception:
        return 0.0
