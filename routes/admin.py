from flask import Blueprint, render_template, redirect, request, flash, url_for
from flask_login import login_required, current_user
from models.ip_autorizada import IPAutorizada
from models.usuario import Usuario
from extensions import db
from models.rol import Rol
from models.asistencia import Asistencia
from datetime import datetime
from datetime import date, datetime, timedelta
from models.horario import Horario
from flask import jsonify, request
from flask import Blueprint, render_template, render_template_string, request, redirect, flash, url_for, jsonify, send_file


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
    from models.horario import Horario
    from datetime import date, datetime, timedelta

    hoy = date.today()
    asistencias = Asistencia.query.filter_by(fecha=hoy).all()

    resumen = []
    for a in asistencias:
        usuario = a.usuario
        horario = Horario.query.filter_by(usuario_id=usuario.id).first()
        hora_inicio = horario.hora_inicio if horario else datetime.strptime("08:00", "%H:%M").time()
        tolerancia = timedelta(minutes=10)

        llego_tarde = False
        if a.hora_entrada and datetime.combine(hoy, a.hora_entrada) > datetime.combine(hoy, hora_inicio) + tolerancia:
            llego_tarde = True

        tiempo_trabajado = "-"
        if a.hora_entrada and a.hora_salida:
            h_entrada = datetime.combine(hoy, a.hora_entrada)
            h_salida = datetime.combine(hoy, a.hora_salida)
            duracion = h_salida - h_entrada
            total_min = int(duracion.total_seconds() // 60)
            horas = total_min // 60
            minutos = total_min % 60
            tiempo_trabajado = f"{horas:02}:{minutos:02}"


        resumen.append({
            "usuario": f"{usuario.nombres} {usuario.apellidos}",
            "entrada": a.hora_entrada.strftime('%H:%M') if a.hora_entrada else "-",
            "salida": a.hora_salida.strftime('%H:%M') if a.hora_salida else "-",
            "llego_tarde": llego_tarde,
            "tiempo": tiempo_trabajado,
            "observaciones": a.observaciones or "-"
        })

    return render_template('admin/partials/resumen_diario_block.html', resumen=resumen, hoy=hoy)
@admin_bp.route('/api/resumen-mensual/html')
def resumen_mensual_html():
    from models.asistencia import Asistencia
    from datetime import datetime, date, timedelta
    from collections import defaultdict

    def formato_hhmm(td):
        if not isinstance(td, timedelta):
            return "-"
        total_minutes = int(td.total_seconds() // 60)
        horas = total_minutes // 60
        minutos = total_minutes % 60
        return f"{horas:02}:{minutos:02}"

    mes_str = request.args.get('mes')
    try:
        if mes_str:
            primer_dia = datetime.strptime(mes_str, "%Y-%m").date()
        else:
            primer_dia = date.today().replace(day=1)
    except ValueError:
        return "Fecha inválida", 400

    # Calcular último día del mes
    mes_siguiente = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo_dia = mes_siguiente - timedelta(days=1)
    dias_del_mes = [(primer_dia + timedelta(days=i)) for i in range((ultimo_dia - primer_dia).days + 1)]

    asistencias = Asistencia.query.filter(
        Asistencia.fecha >= primer_dia,
        Asistencia.fecha <= ultimo_dia
    ).all()

    resumen = defaultdict(lambda: defaultdict(str))
    total_por_usuario = defaultdict(timedelta)

    for a in asistencias:
        if a.hora_entrada and a.hora_salida:
            h_entrada = datetime.combine(a.fecha, a.hora_entrada)
            h_salida = datetime.combine(a.fecha, a.hora_salida)
            duracion = h_salida - h_entrada
            resumen[a.usuario][a.fecha] = formato_hhmm(duracion)
            total_por_usuario[a.usuario] += duracion
        else:
            resumen[a.usuario][a.fecha] = "-"

    # Redondear total en formato HH:MM
    total_por_usuario_fmt = {u: formato_hhmm(t) for u, t in total_por_usuario.items()}

    return render_template('admin/partials/resumen_mensual_block.html',
                           resumen=resumen,
                           dias=dias_del_mes,
                           total_por_usuario=total_por_usuario_fmt,
                           mes=primer_dia.strftime('%Y-%m'))

@admin_bp.route('/api/por-usuario/html')
def por_usuario_html():
    from models.usuario import Usuario
    usuarios = Usuario.query.order_by(Usuario.nombres).all()
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
@admin_bp.route('/api/resumen-mensual/exportar')
def exportar_resumen_excel():
    import io
    import pandas as pd
    from flask import send_file
    from datetime import datetime, timedelta
    from collections import defaultdict
    from models.asistencia import Asistencia
    from models.usuario import Usuario

    def formato_hhmm(td):
        if not isinstance(td, timedelta):
            return "-"
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
    dias = [(primer_dia + timedelta(days=i)) for i in range((ultimo_dia - primer_dia).days + 1)]

    asistencias = Asistencia.query.filter(
        Asistencia.fecha >= primer_dia,
        Asistencia.fecha <= ultimo_dia
    ).order_by(Asistencia.usuario_id, Asistencia.fecha).all()

    resumen = defaultdict(lambda: defaultdict(str))
    total_por_usuario = defaultdict(timedelta)

    for a in asistencias:
        if a.hora_entrada and a.hora_salida:
            h_entrada = datetime.combine(a.fecha, a.hora_entrada)
            h_salida = datetime.combine(a.fecha, a.hora_salida)
            duracion = h_salida - h_entrada
            resumen[a.usuario][a.fecha] = formato_hhmm(duracion)
            total_por_usuario[a.usuario] += duracion
        else:
            resumen[a.usuario][a.fecha] = "-"

    # Construir DataFrame
    columnas = [str(d.day) for d in dias]
    data = []

    for u in resumen:
        fila = {
            "Usuario": f"{u.nombres} {u.apellidos}",
            **{str(d.day): resumen[u][d] for d in dias},
            "Total": formato_hhmm(total_por_usuario[u])
        }
        data.append(fila)

    df = pd.DataFrame(data)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Resumen Mensual')
        workbook = writer.book
        worksheet = writer.sheets['Resumen Mensual']

        # 🧾 Formato personalizado
        formato_pequeno = workbook.add_format({'font_size': 8, 'text_wrap': True})
        worksheet.set_column(0, len(df.columns)-1, 12, formato_pequeno)

    output.seek(0)
    filename = f"resumen_mensual_{mes_str}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@admin_bp.route('/api/resumen-mensual/exportar-pdf')
def exportar_resumen_pdf():
    from flask import render_template_string
    from weasyprint import HTML
    import io
    from datetime import datetime, timedelta
    from collections import defaultdict
    from models.asistencia import Asistencia

    def formato_hhmm(td):
        if not isinstance(td, timedelta):
            return "-"
        total_minutes = int(td.total_seconds() // 60)
        horas = total_minutes // 60
        minutos = total_minutes % 60
        return f"{horas:02}:{minutos:02}"

    mes_str = request.args.get('mes')
    try:
        primer_dia = datetime.strptime(mes_str, "%Y-%m").date()
    except:
        return "Mes inválido", 400

    mes_siguiente = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)
    ultimo_dia = mes_siguiente - timedelta(days=1)
    dias = [(primer_dia + timedelta(days=i)) for i in range((ultimo_dia - primer_dia).days + 1)]

    asistencias = Asistencia.query.filter(
        Asistencia.fecha >= primer_dia,
        Asistencia.fecha <= ultimo_dia
    ).order_by(Asistencia.usuario_id, Asistencia.fecha).all()

    resumen = defaultdict(lambda: defaultdict(str))
    total_por_usuario = defaultdict(timedelta)

    for a in asistencias:
        if a.hora_entrada and a.hora_salida:
            h_entrada = datetime.combine(a.fecha, a.hora_entrada)
            h_salida = datetime.combine(a.fecha, a.hora_salida)
            duracion = h_salida - h_entrada
            resumen[a.usuario][str(a.fecha.day)] = formato_hhmm(duracion)
            total_por_usuario[a.usuario] += duracion
        else:
            resumen[a.usuario][str(a.fecha.day)] = "-"

    total_por_usuario_fmt = {u: formato_hhmm(t) for u, t in total_por_usuario.items()}
    dias_numeros = [str(d.day) for d in dias]

    html = render_template_string("""
    <html>
    <head>
<style>
    @page {
        size: A4 landscape;
        margin: 30px;
    }
    body {
        font-family: sans-serif;
        font-size: 6pt;
        margin: 30px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 6pt;
    }
    th, td {
        border: 1px solid #333;
        padding: 2px;
        text-align: center;
    }
    th:first-child, td:first-child {
        text-align: left;
    }
    th {
        background-color: #f0f0f0;
    }
</style>

    </head>
    <body>
    <h3>Resumen Mensual - {{ mes }}</h3>
    <table>
        <thead>
            <tr>
                <th>Usuario</th>
                {% for dia in dias %}
                <th>{{ dia }}</th>
                {% endfor %}
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {% for u, dias_u in resumen.items() %}
            <tr>
                <td>{{ u.nombres }} {{ u.apellidos }}</td>
                {% for d in dias %}
                <td>{{ dias_u.get(d, "-") }}</td>
                {% endfor %}
                <td>{{ total_por_usuario[u] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </body>
    </html>
    """, resumen=resumen, total_por_usuario=total_por_usuario_fmt, dias=dias_numeros, mes=mes_str)

    pdf_io = io.BytesIO()
    HTML(string=html).write_pdf(pdf_io, stylesheets=[], presentational_hints=True)
    pdf_io.seek(0)

    return send_file(pdf_io, download_name=f"resumen_mensual_{mes_str}.pdf", as_attachment=True)
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
