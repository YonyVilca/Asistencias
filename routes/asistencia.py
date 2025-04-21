from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_required, current_user
from models.asistencia import Asistencia
from models.ip_autorizada import IPAutorizada
from models.horario import Horario
from extensions import db
from datetime import date, datetime
from datetime import date, datetime, timedelta


asistencia_bp = Blueprint('asistencia', __name__)

@asistencia_bp.route('/')
@login_required
def dashboard():
    if current_user.rol.nombre == 'admin':
        return redirect(url_for('admin.reportes'))

    from datetime import datetime, timedelta

    hoy = date.today()
    ip = request.remote_addr
    asistencia = Asistencia.query.filter_by(usuario_id=current_user.id, fecha=hoy).first()

    mensaje_bienvenida = None
    ip_autorizada = IPAutorizada.query.filter_by(ip=ip, activa=True).first()

    if ip_autorizada:
        if asistencia and asistencia.hora_entrada and not asistencia.hora_salida:
            mensaje_bienvenida = {
                'entrada': asistencia.hora_entrada.strftime('%H:%M')
            }
        elif not asistencia:
            mensaje_bienvenida = {
                'entrada': None
            }

    return render_template('dashboard.html',
                           usuario=current_user,
                           asistencia=asistencia,
                           mensaje_bienvenida=mensaje_bienvenida)


@asistencia_bp.route('/marcar', methods=['POST'])
@login_required
def marcar():
    hoy = date.today()
    ahora = datetime.now().time()
    ip = request.remote_addr

    # ⛔ Validación de IP
    ip_autorizada = IPAutorizada.query.filter_by(ip=ip, activa=True).first()
    if not ip_autorizada:
        #flash(f"⛔ La IP {ip} no está autorizada para marcar asistencia.", "danger")
        flash(f"⛔  No está autorizada para marcar asistencia.", "danger")
        return redirect(url_for('asistencia.dashboard'))

    # Parámetros del horario
    hora_inicio = datetime.strptime("08:00", "%H:%M").time()
    hora_fin = datetime.strptime("17:00", "%H:%M").time()
    tolerancia_entrada = timedelta(minutes=10)
    tolerancia_salida = timedelta(minutes=10)
    margen_inicio = datetime.strptime("07:50", "%H:%M").time()
    margen_fin = datetime.strptime("17:10", "%H:%M").time()

    asistencia = Asistencia.query.filter_by(usuario_id=current_user.id, fecha=hoy).first()
    observacion = ""

    # Verificar si está fuera del rango permitido
    if ahora < margen_inicio or ahora > margen_fin:
        flash("❌ Solo puedes marcar asistencia durante el horario laboral.", "danger")
        return redirect(url_for('asistencia.dashboard'))

    if not asistencia:
        # Entrada
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
    elif not asistencia.hora_salida:
        # Salida
        if ahora > margen_fin:
            asistencia.hora_salida = hora_fin
            asistencia.observaciones = (asistencia.observaciones or "") + " ⚠️ Auto salida"
            flash("⚠️ No marcaste salida a tiempo. Se asignó automáticamente 17:00.", "warning")
        else:
            asistencia.hora_salida = ahora
            flash("🚪 Salida registrada correctamente.", "info")
    else:
        flash("⚠️ Ya registraste tu entrada y salida hoy.", "warning")

    db.session.commit()
    return redirect(url_for('asistencia.dashboard'))

