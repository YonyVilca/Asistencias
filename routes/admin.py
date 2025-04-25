from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user
from models.ip_autorizada import IPAutorizada
from models.usuario import Usuario
from extensions import db
from models.rol import Rol
from models.asistencia import Asistencia
from datetime import datetime
from datetime import datetime, date, time, timedelta
from datetime import timedelta

from models.horario import Horario
from flask import jsonify, request
from flask import Blueprint, render_template, render_template_string, request, redirect, flash, url_for, jsonify, send_file
from models.asistencia import Asistencia
from collections import defaultdict


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def es_admin():
    return current_user.rol.nombre == 'admin'

@admin_bp.before_request
@login_required
def restringir_solo_admin():
    if not es_admin():
        flash("⚠️ No tienes permisos para acceder a esta sección.", "danger")
        return redirect(url_for('asistencia.dashboard'))

# 🌐 Ver todas las IPs autorizadas
@admin_bp.route('/ips')
def listar_ips():
    ips = IPAutorizada.query.order_by(IPAutorizada.ip).all()
    return render_template('admin/ips.html', ips=ips)

# ➕ Agregar nueva IP
@admin_bp.route('/ips/agregar', methods=['POST'])
def agregar_ip():
    nueva_ip = request.form['ip']
    descripcion = request.form.get('descripcion', '')

    if IPAutorizada.query.filter_by(ip=nueva_ip).first():
        flash("❗La IP ya existe.", "warning")
    else:
        nueva = IPAutorizada(ip=nueva_ip, descripcion=descripcion, activa=True)
        db.session.add(nueva)
        db.session.commit()
        flash("✅ IP agregada exitosamente.", "success")

    return redirect(url_for('admin.listar_ips'))

# ✅ Activar / ❌ Desactivar IP
@admin_bp.route('/ips/toggle/<int:ip_id>')
def cambiar_estado_ip(ip_id):
    ip = IPAutorizada.query.get_or_404(ip_id)
    ip.activa = not ip.activa
    db.session.commit()
    flash(f"🔄 Estado actualizado: {'Activa' if ip.activa else 'Inactiva'}", "info")
    return redirect(url_for('admin.listar_ips'))

# 🗑️ Eliminar IP
@admin_bp.route('/ips/eliminar/<int:ip_id>')
def eliminar_ip(ip_id):
    ip = IPAutorizada.query.get_or_404(ip_id)
    db.session.delete(ip)
    db.session.commit()
    flash("🗑️ IP eliminada correctamente.", "success")
    return redirect(url_for('admin.listar_ips'))

# 🌐 Ver todos los usuarios
@admin_bp.route('/usuarios')
def listar_usuarios():
    usuarios = Usuario.query.filter_by(eliminado=False).order_by(Usuario.fecha_registro.desc()).all()
    roles = Rol.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios, roles=roles)



# 🔄 Activar/Inactivar usuario
@admin_bp.route('/usuarios/toggle/<int:usuario_id>')
def toggle_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.nombre_usuario == "admin":
        flash("⚠️ No puedes desactivar al superadministrador.", "warning")
    else:
        usuario.estado = not usuario.estado
        db.session.commit()
        flash(f"🧍 Usuario {'activado' if usuario.estado else 'desactivado'} correctamente.", "success")
    return redirect(url_for('admin.listar_usuarios'))
@admin_bp.route('/usuarios/crear', methods=['POST'])
def crear_usuario_ip():
    from werkzeug.security import generate_password_hash

    nombre_usuario = request.form['nombre_usuario']
    nombres = request.form['nombres']
    apellidos = request.form['apellidos']
    password = request.form['password']
    rol_id = request.form['rol_id']

    if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
        flash("❗Ese nombre de usuario ya existe.", "warning")
    else:
        nuevo = Usuario(
            nombre_usuario=nombre_usuario,
            nombres=nombres,
            apellidos=apellidos,
            rol_id=int(rol_id),
            estado=True
        )
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()
        flash("✅ Usuario creado exitosamente.", "success")

    return redirect(url_for('admin.listar_usuarios'))
@admin_bp.route('/usuarios/crear', methods=['POST'])
def crear_usuario():
    from werkzeug.security import generate_password_hash
    from models.usuario import Usuario
    from models.rol import Rol

    nombre_usuario = request.form['nombre_usuario'].strip().lower()
    nombres = request.form['nombres'].strip()
    apellidos = request.form['apellidos'].strip()
    password = request.form['password']
    rol_id = request.form['rol_id']

    # ❌ Validaciones
    if len(password) < 6:
        flash("❗La contraseña debe tener al menos 6 caracteres.", "warning")
        return redirect(url_for('admin.listar_usuarios'))

    if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
        flash("❗El nombre de usuario ya existe.", "warning")
        return redirect(url_for('admin.listar_usuarios'))

    if Usuario.query.filter_by(nombres=nombres, apellidos=apellidos).first():
        flash("❗Ya existe un usuario con ese nombre completo.", "warning")
        return redirect(url_for('admin.listar_usuarios'))

    # ✅ Crear usuario
    nuevo = Usuario(
        nombre_usuario=nombre_usuario,
        nombres=nombres,
        apellidos=apellidos,
        rol_id=int(rol_id),
        estado=True
    )
    nuevo.set_password(password)
    db.session.add(nuevo)
    db.session.commit()
    flash("✅ Usuario creado exitosamente.", "success")

    return redirect(url_for('admin.listar_usuarios'))

@admin_bp.route('/usuarios/restablecer/<int:usuario_id>')
def restablecer_contrasena(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.nombre_usuario == 'admin':
        flash("⚠️ No puedes restablecer la contraseña del superadministrador desde aquí.", "warning")
        return redirect(url_for('admin.listar_usuarios'))

    usuario.set_password("usuario123")  # contraseña temporal
    usuario.primer_inicio = True
    db.session.commit()

    flash(f"🔁 Contraseña restablecida para {usuario.nombre_usuario}. Usar: usuario123", "info")
    return redirect(url_for('admin.listar_usuarios'))
@admin_bp.route('/reportes', methods=['GET', 'POST'])
def reportes():
    usuarios = Usuario.query.order_by(Usuario.nombres).all()
    asistencias = []

    if request.method == 'POST':
        usuario_id = request.form.get('usuario_id')
        desde = request.form.get('desde')
        hasta = request.form.get('hasta')

        query = Asistencia.query

        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)

        if desde:
            query = query.filter(Asistencia.fecha >= desde)

        if hasta:
            query = query.filter(Asistencia.fecha <= hasta)

        asistencias = query.order_by(Asistencia.fecha.asc()).all()

    return render_template('admin/reportes.html', usuarios=usuarios, asistencias=asistencias)

@admin_bp.route('/resumen-diario')
def resumen_diario():
    # Esta solo devuelve el HTML vacío con contenedor y JS
    return render_template('admin/resumen_diario.html')

@admin_bp.route('/api/resumen-diario/html')
def resumen_diario_html():
    from models.asistencia import Asistencia
    from models.usuario import Usuario
    from datetime import datetime, date, time, timedelta
    from collections import defaultdict

    hoy = date.today()

    def calcular_pendientes_mensuales(usuario_id: int, desde: date, hasta: date):
        asistencias = Asistencia.query.filter(
            Asistencia.usuario_id == usuario_id,
            Asistencia.fecha >= desde,
            Asistencia.fecha <= hasta
        ).order_by(Asistencia.fecha, Asistencia.hora_entrada).all()

        bloques_por_dia = defaultdict(list)
        for a in asistencias:
            if a.hora_entrada and a.hora_salida:
                entrada = datetime.combine(a.fecha, a.hora_entrada)
                salida = datetime.combine(a.fecha, a.hora_salida)
                bloques_por_dia[a.fecha].append((entrada, salida))

        total_trabajado = timedelta()
        for fecha, bloques in bloques_por_dia.items():
            tiempo_dia = sum((s - e for e, s in bloques), timedelta())
            total_trabajado += tiempo_dia

        # ✅ Nuevo cálculo correcto del esperado
        esperado = timedelta()
        dia_actual = desde
        while dia_actual <= hasta:
            if dia_actual.weekday() in [0,1,2,3,4]:  # Lunes a Viernes
                esperado += timedelta(hours=9)
            elif dia_actual.weekday() == 5:  # Sábado
                esperado += timedelta(hours=5)
            dia_actual += timedelta(days=1)

        diferencia = esperado - total_trabajado
        diferencia_abs = abs(diferencia.total_seconds())
        horas_pendientes = int(diferencia_abs // 3600)
        minutos_pendientes = int((diferencia_abs % 3600) // 60)
        saldo_signo = "+" if diferencia.total_seconds() > 0 else "-"

        return horas_pendientes, minutos_pendientes, saldo_signo

    # Configuración de jornada y tolerancia
    hora_inicio = time(8, 0)
    tolerancia_entrada = timedelta(minutes=10)

    usuarios = Usuario.query.filter(Usuario.rol.has(nombre='empleado')).all()
    asistencias = Asistencia.query.join(Usuario).filter(
        Asistencia.fecha == hoy,
        Usuario.rol.has(nombre='empleado')
    ).order_by(Asistencia.usuario_id, Asistencia.hora_entrada).all()

    registros = defaultdict(list)
    estados = {}

    for a in asistencias:
        if a.hora_entrada:
            registros[a.usuario_id].append(a)

    for usuario in usuarios:
        bloques = registros.get(usuario.id, [])
        horas_pendientes, minutos_pendientes, saldo_signo = calcular_pendientes_mensuales(
            usuario.id, hoy.replace(day=1), hoy
        )

        if not bloques:
            estados[usuario] = {
                "entrada": "-",
                "salida": "-",
                "observacion": "Ausente",
                "total": "-",
                "horas_pendientes": horas_pendientes,
                "minutos_pendientes": minutos_pendientes,
                "saldo_signo": saldo_signo,
                "color": "danger"
            }
            continue

        primera_entrada = min(b.hora_entrada for b in bloques if b.hora_entrada)
        ultima_salida = max((b.hora_salida for b in bloques if b.hora_salida), default=None)

        entrada_str = primera_entrada.strftime('%H:%M') if primera_entrada else "-"
        salida_str = ultima_salida.strftime('%H:%M') if ultima_salida else "-"

        jornada_completa = timedelta()
        for b in bloques:
            if b.hora_entrada and b.hora_salida:
                entrada_dt = datetime.combine(hoy, b.hora_entrada)
                salida_dt = datetime.combine(hoy, b.hora_salida)
                jornada_completa += salida_dt - entrada_dt

        total_horas = int(jornada_completa.total_seconds() // 3600)
        total_minutos = int((jornada_completa.total_seconds() % 3600) // 60)
        total_str = f"{total_horas:02}:{total_minutos:02}"

        if primera_entrada > (datetime.combine(hoy, hora_inicio) + tolerancia_entrada).time():
            observacion = "Tardanza"
            color = "warning"
        elif primera_entrada < hora_inicio:
            observacion = "Temprano"
            color = "success"
        else:
            observacion = "A tiempo"
            color = "success"

        estados[usuario] = {
            "entrada": entrada_str,
            "salida": salida_str,
            "observacion": observacion,
            "total": total_str,
            "horas_pendientes": horas_pendientes,
            "minutos_pendientes": minutos_pendientes,
            "saldo_signo": saldo_signo,
            "color": color
        }

    # ✅ Aseguramos que el return exista siempre
    return render_template("admin/partials/resumen_diario_block.html", estados=estados, hoy=hoy)

@admin_bp.route('/api/por-usuario/html')
def por_usuario_html():
    from models.usuario import Usuario
    usuarios = Usuario.query.filter(Usuario.rol.has(nombre='empleado')).order_by(Usuario.nombres).all()
    current_month = datetime.today().strftime('%Y-%m')
    return render_template('admin/partials/por_usuario_block.html',
                           usuarios=usuarios,
                           current_month=current_month)
@admin_bp.route('/api/asistencias-usuario')
def asistencias_usuario_html():
    from models.asistencia import Asistencia
    from models.usuario import Usuario
    from datetime import datetime, timedelta

    usuario_id = request.args.get('usuario_id')
    mes_str = request.args.get('mes')

    if not usuario_id:
        return "ID inválido", 400

    usuario = Usuario.query.get_or_404(usuario_id)

    try:
        if mes_str:
            primer_dia = datetime.strptime(mes_str, "%Y-%m").date()
        else:
            primer_dia = datetime.today().replace(day=1)
    except ValueError:
        return "Mes inválido", 400

    # Calcular último día del mes
    mes_siguiente = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo_dia = mes_siguiente - timedelta(days=1)

    asistencias = Asistencia.query.filter(
        Asistencia.usuario_id == usuario.id,
        Asistencia.fecha >= primer_dia,
        Asistencia.fecha <= ultimo_dia
    ).order_by(Asistencia.fecha.asc()).all()

    return render_template('admin/partials/tabla_asistencias_usuario.html',
                           usuario=usuario,
                           asistencias=asistencias,
                           mes=primer_dia.strftime('%Y-%m'))

@admin_bp.route('/api/asistencias-usuario/exportar')
def exportar_asistencias_excel():
    import io
    import pandas as pd
    from flask import send_file
    from models.asistencia import Asistencia
    from models.usuario import Usuario
    from datetime import datetime, timedelta

    usuario_id = request.args.get('usuario_id')
    mes_str = request.args.get('mes')

    if not usuario_id or not mes_str:
        return "Parámetros faltantes", 400

    usuario = Usuario.query.get_or_404(usuario_id)
    primer_dia = datetime.strptime(mes_str, "%Y-%m").date()
    mes_siguiente = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo_dia = mes_siguiente - timedelta(days=1)

    asistencias = Asistencia.query.filter(
        Asistencia.usuario_id == usuario.id,
        Asistencia.fecha >= primer_dia,
        Asistencia.fecha <= ultimo_dia
    ).order_by(Asistencia.fecha.asc()).all()

    data = [{
        "Fecha": a.fecha,
        "Hora Entrada": a.hora_entrada or "-",
        "Hora Salida": a.hora_salida or "-",
        "IP": a.ip or "-",
        "Observaciones": a.observaciones or "-"
    } for a in asistencias]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Asistencias')

    output.seek(0)
    filename = f"asistencias_{usuario.nombre_usuario}_{mes_str}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@admin_bp.route('/asistencias/editar/<int:asistencia_id>', methods=['GET', 'POST'])
def editar_asistencia(asistencia_id):
    asistencia = Asistencia.query.get_or_404(asistencia_id)

    if request.method == 'POST':
        nueva_entrada = request.form.get('hora_entrada')
        nueva_salida = request.form.get('hora_salida')
        nueva_obs = request.form.get('observaciones', '').strip()

        asistencia.hora_entrada = datetime.strptime(nueva_entrada, '%H:%M').time() if nueva_entrada else None
        asistencia.hora_salida = datetime.strptime(nueva_salida, '%H:%M').time() if nueva_salida else None
        asistencia.observaciones = nueva_obs or None

        db.session.commit()
        flash("✅ Asistencia actualizada correctamente.", "success")
        return redirect(url_for('admin.reportes'))

    return render_template('admin/editar_asistencia.html', asistencia=asistencia)
@admin_bp.route('/usuarios/eliminar/<int:usuario_id>')
def eliminar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if usuario.nombre_usuario == "admin":
        flash("⚠️ No puedes eliminar al superadministrador.", "warning")
        return redirect(url_for('admin.listar_usuarios'))

    usuario.eliminado = True
    db.session.commit()
    flash("🗑️ Usuario eliminado lógicamente.", "info")
    return redirect(url_for('admin.listar_usuarios'))
@admin_bp.route('/api/resumen-semanal/html')
def resumen_semanal_html():
    from datetime import datetime, timedelta
    from models.asistencia import Asistencia
    from models.usuario import Usuario
    from collections import defaultdict

    def formato_hhmm(td):
        total_minutes = int(td.total_seconds() // 60)
        horas = total_minutes // 60
        minutos = total_minutes % 60
        return f"{horas:02}:{minutos:02}"

    def obtener_rango_semana(mes_str, semana_idx):
        primer_dia_mes = datetime.strptime(mes_str, "%Y-%m").date()

        # Avanzar hasta el primer lunes del mes o anterior
        dia_inicio = primer_dia_mes
        while dia_inicio.weekday() != 0:
            dia_inicio -= timedelta(days=1)

        dia_inicio += timedelta(weeks=semana_idx - 1)
        dia_fin = dia_inicio + timedelta(days=5)  # Lunes a Sábado

        # ✅ Solo días dentro del mes solicitado
        dias_validos = [
            dia for dia in (dia_inicio + timedelta(days=i) for i in range(6))
            if dia.month == primer_dia_mes.month
        ]
        return dias_validos

    mes_str = request.args.get("mes", datetime.today().strftime("%Y-%m"))
    semana = int(request.args.get("semana", 1))
    dias_semana = obtener_rango_semana(mes_str, semana)

    usuarios = Usuario.query.filter(Usuario.rol.has(nombre='empleado')).all()
    asistencias = Asistencia.query.filter(
        Asistencia.fecha.in_(dias_semana)
    ).order_by(Asistencia.usuario_id, Asistencia.fecha).all()

    resumen = defaultdict(lambda: defaultdict(timedelta))
    total_por_usuario = defaultdict(timedelta)
    esperado_por_usuario = {}
    diferencia_por_usuario = {}

    for a in asistencias:
        if a.hora_entrada and a.hora_salida:
            entrada = datetime.combine(a.fecha, a.hora_entrada)
            salida = datetime.combine(a.fecha, a.hora_salida)
            duracion = salida - entrada
            resumen[a.usuario][a.fecha] += duracion
            total_por_usuario[a.usuario] += duracion

    for u in usuarios:
        esperado = timedelta()
        for dia in dias_semana:
            if dia.weekday() == 5:  # Sábado
                esperado += timedelta(hours=5)
            else:
                esperado += timedelta(hours=9)
        trabajado = total_por_usuario.get(u, timedelta())
        diferencia = trabajado - esperado

        esperado_por_usuario[u] = formato_hhmm(esperado)
        diferencia_por_usuario[u] = (
            f"{'-' if diferencia.total_seconds() < 0 else '+'}{formato_hhmm(abs(diferencia))}"
        )

    resumen_fmt = {
        usuario: {
            dia: formato_hhmm(resumen[usuario][dia]) if dia in resumen[usuario] else "-"
            for dia in dias_semana
        }
        for usuario in usuarios
    }

    total_fmt = {u: formato_hhmm(t) for u, t in total_por_usuario.items()}

    return render_template(
        "admin/partials/resumen_semanal_block.html",
        resumen=resumen_fmt,
        total_por_usuario=total_fmt,
        esperado_por_usuario=esperado_por_usuario,  # ✅ corregido
        diferencia_por_usuario=diferencia_por_usuario,  # ✅ corregido
        dias=dias_semana,
        semana=semana,
        mes=mes_str,
        hoy=datetime.today().date(),
        timedelta=timedelta
    )
@admin_bp.route('/api/exportar-reporte-mensual')
def exportar_reporte_mensual():
    import io
    import pandas as pd
    from flask import send_file
    from datetime import datetime, timedelta
    from collections import defaultdict
    from models.asistencia import Asistencia
    from models.usuario import Usuario

    def formato_hhmm(td):
        total_minutes = int(td.total_seconds() // 60)
        horas = total_minutes // 60
        minutos = total_minutes % 60
        return f"{horas:02}:{minutos:02}"

    mes_str = request.args.get('mes')
    if not mes_str:
        return "Mes requerido", 400

    try:
        primer_dia = datetime.strptime(mes_str, "%Y-%m").date()
    except ValueError:
        return "Formato de mes inválido", 400

    mes_siguiente = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo_dia = mes_siguiente - timedelta(days=1)
    dias_del_mes = [(primer_dia + timedelta(days=i)) for i in range((ultimo_dia - primer_dia).days + 1)]

    usuarios = Usuario.query.filter(Usuario.rol.has(nombre='empleado')).all()
    asistencias = Asistencia.query.filter(
        Asistencia.fecha >= primer_dia,
        Asistencia.fecha <= ultimo_dia
    ).order_by(Asistencia.usuario_id, Asistencia.fecha, Asistencia.hora_entrada).all()

    resumen = defaultdict(lambda: {
        'trabajadas': timedelta(),
        'esperadas': timedelta(),
        'tardanzas': 0,
        'faltas': 0
    })

    registros = defaultdict(list)
    for a in asistencias:
        registros[a.usuario_id].append(a)

    for usuario in usuarios:
        for dia in dias_del_mes:
            dia_asistencias = [a for a in registros[usuario.id] if a.fecha == dia]

            esperado = timedelta(hours=9) if dia.weekday() < 5 else (timedelta(hours=5) if dia.weekday() == 5 else timedelta())
            resumen[usuario]['esperadas'] += esperado

            if not dia_asistencias:
                if dia.weekday() < 6:  # lunes a sábado
                    resumen[usuario]['faltas'] += 1
                continue

            bloques = []
            for a in dia_asistencias:
                if a.hora_entrada and a.hora_salida:
                    entrada = datetime.combine(a.fecha, a.hora_entrada)
                    salida = datetime.combine(a.fecha, a.hora_salida)
                    bloques.append((entrada, salida))

            if bloques:
                total_dia = sum((s - e for e, s in bloques), timedelta())
                resumen[usuario]['trabajadas'] += total_dia

                primera_entrada = min(e.time() for e, _ in bloques)
                if primera_entrada > time(8, 10):  # tardanza después de 8:10
                    resumen[usuario]['tardanzas'] += 1

    data = []
    for usuario, info in resumen.items():
        trabajadas = info['trabajadas']
        esperadas = info['esperadas']
        diferencia = trabajadas - esperadas

        data.append({
            "Usuario": f"{usuario.nombres} {usuario.apellidos}",
            "Horas Trabajadas": formato_hhmm(trabajadas),
            "Horas Esperadas": formato_hhmm(esperadas),
            "Diferencia": ("-" if diferencia.total_seconds() < 0 else "+") + formato_hhmm(abs(diferencia)),
            "Tardanzas": info['tardanzas'],
            "Faltas": info['faltas']
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte Mensual')
        workbook = writer.book
        worksheet = writer.sheets['Reporte Mensual']
        formato_pequeno = workbook.add_format({'font_size': 10, 'text_wrap': True})
        worksheet.set_column(0, len(df.columns)-1, 20, formato_pequeno)

    output.seek(0)
    filename = f"reporte_mensual_{mes_str}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
