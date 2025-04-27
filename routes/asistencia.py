from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user
from models.asistencia import Asistencia
from models.ip_autorizada import IPAutorizada
from models.vinculo_telegram import VinculoTelegram
from extensions import db
from datetime import date, datetime, timedelta, time
from collections import defaultdict
import random
import string

asistencia_bp = Blueprint('asistencia', __name__)

def generar_codigo_corto():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@asistencia_bp.route('/')
@login_required
def home_redirect():
    if current_user.rol.nombre == 'admin':
        return redirect(url_for('admin.reportes'))
    return redirect(url_for('asistencia.dashboard'))


@asistencia_bp.route('/dashboard')
@login_required
def dashboard():
    hoy = date.today()
    ip = request.remote_addr
    usuario = current_user

    asistencias_dia = Asistencia.query.filter_by(
        usuario_id=usuario.id,
        fecha=hoy
    ).order_by(Asistencia.hora_entrada).all()

    ip_autorizada = IPAutorizada.query.filter_by(ip=ip, activa=True).first()

    mensaje_bienvenida = None
    if ip_autorizada:
        if asistencias_dia and asistencias_dia[0].hora_entrada and not asistencias_dia[0].hora_salida:
            mensaje_bienvenida = { 'entrada': asistencias_dia[0].hora_entrada.strftime('%H:%M') }
        elif not asistencias_dia:
            mensaje_bienvenida = { 'entrada': None }

    # Calcular tiempo del día
    bloques_hoy = []
    for a in asistencias_dia:
        if a.hora_entrada and a.hora_salida:
            entrada = datetime.combine(hoy, a.hora_entrada)
            salida = datetime.combine(hoy, a.hora_salida)
            bloques_hoy.append((entrada, salida))

    tiempo_hoy = sum((s - e for e, s in bloques_hoy), timedelta())
    segundos_hoy = tiempo_hoy.total_seconds()
    horas = int(segundos_hoy // 3600)
    minutos = int((segundos_hoy % 3600) // 60)

    # Cálculo mensual actualizado con lógica semanal
    primer_dia_mes = hoy.replace(day=1)
    asistencias_mes = Asistencia.query.filter(
        Asistencia.usuario_id == usuario.id,
        Asistencia.fecha >= primer_dia_mes,
        Asistencia.fecha <= hoy
    ).order_by(Asistencia.fecha, Asistencia.hora_entrada).all()

    bloques_por_dia = defaultdict(list)
    for a in asistencias_mes:
        if a.hora_entrada and a.hora_salida:
            entrada = datetime.combine(a.fecha, a.hora_entrada)
            salida = datetime.combine(a.fecha, a.hora_salida)
            bloques_por_dia[a.fecha].append((entrada, salida))

    total_trabajado = timedelta()
    esperado = timedelta()

    for fecha, bloques in bloques_por_dia.items():
        tiempo_dia = sum((s - e for e, s in bloques), timedelta())
        total_trabajado += tiempo_dia

    # Calcular esperado en base a calendario
    dia_actual = primer_dia_mes
    while dia_actual <= hoy:
        if dia_actual.weekday() in [0, 1, 2, 3, 4]:  # Lunes a Viernes
            esperado += timedelta(hours=9)
        elif dia_actual.weekday() == 5:  # Sábado
            esperado += timedelta(hours=5)
        # domingo no se suma
        dia_actual += timedelta(days=1)

    diferencia = esperado - total_trabajado
    diferencia_abs = abs(diferencia.total_seconds())
    horas_pendientes = int(diferencia_abs // 3600)
    minutos_pendientes = int((diferencia_abs % 3600) // 60)
    saldo_signo = "+" if diferencia.total_seconds() > 0 else "-"

    # Token corto Telegram
    token_corto = None
    if not current_user.telegram_id:
        VinculoTelegram.query.filter(
            VinculoTelegram.usuario_id == current_user.id,
            VinculoTelegram.fecha_creacion < datetime.utcnow() - timedelta(minutes=10)
        ).delete()

        existente = VinculoTelegram.query.filter_by(usuario_id=current_user.id).first()
        if existente and not existente.expirado():
            token_corto = existente.codigo
        else:
            nuevo_codigo = generar_codigo_corto()
            while VinculoTelegram.query.filter_by(codigo=nuevo_codigo).first():
                nuevo_codigo = generar_codigo_corto()
            vinculo = VinculoTelegram(usuario_id=current_user.id, codigo=nuevo_codigo)
            db.session.add(vinculo)
            db.session.commit()
            token_corto = nuevo_codigo

    return render_template('dashboard.html',
                           usuario=usuario,
                           mensaje_bienvenida=mensaje_bienvenida,
                           asistencias=asistencias_dia,
                           horas=horas,
                           minutos=minutos,
                           horas_pendientes=horas_pendientes,
                           minutos_pendientes=minutos_pendientes,
                           saldo_signo=saldo_signo,
                           token_vinculacion=token_corto,
                           datetime=datetime)

@asistencia_bp.route('/marcar', methods=['POST'])
@login_required
def marcar():
    hoy = date.today()
    ahora = datetime.now().time()
    ip = request.remote_addr
    tipo = request.form.get('tipo')

    ip_autorizada = IPAutorizada.query.filter_by(ip=ip, activa=True).first()
    if not ip_autorizada:
        flash("⛔ No está autorizado para marcar asistencia.", "danger")
        return redirect(url_for('asistencia.dashboard'))

    hora_minima_entrada = time(5, 0)
    hora_inicio = time(8, 0)
    tolerancia_entrada = timedelta(minutes=10)
    hora_fin_laboral = time(18, 0)

    asistencias = Asistencia.query.filter_by(
        usuario_id=current_user.id,
        fecha=hoy
    ).order_by(Asistencia.hora_entrada).all()
    ultima = asistencias[-1] if asistencias else None

    if tipo == 'entrada':
        if ultima and not ultima.hora_salida:
            flash("⚠️ Debes marcar salida antes de registrar otra entrada.", "warning")
            return redirect(url_for('asistencia.dashboard'))

        if ahora < hora_minima_entrada:
            flash("❌ No se permite registrar entrada antes de las 07:55 a.m.", "danger")
            return redirect(url_for('asistencia.dashboard'))

        observacion = ""
        if ahora > (datetime.combine(hoy, hora_inicio) + tolerancia_entrada).time():
            observacion = "⏰ Tardanza"

        nueva = Asistencia(
            usuario_id=current_user.id,
            fecha=hoy,
            hora_entrada=ahora,
            ip=ip,
            observaciones=observacion or None
        )
        db.session.add(nueva)
        flash("✅ Entrada registrada correctamente.", "success")

    elif tipo == 'salida':
        if not ultima or ultima.hora_salida:
            flash("⚠️ No hay una entrada abierta para marcar salida.", "warning")
            return redirect(url_for('asistencia.dashboard'))

        ultima.hora_salida = ahora
        flash("🚪 Salida registrada correctamente.", "info")

    db.session.commit()
    return redirect(url_for('asistencia.dashboard'))



@asistencia_bp.route('/desvincular-telegram', methods=['POST'])
@login_required
def desvincular_telegram():
    current_user.telegram_id = None
    db.session.commit()
    flash("Tu cuenta de Telegram fue desvinculada correctamente.", "info")
    return redirect(url_for('asistencia.dashboard'))
