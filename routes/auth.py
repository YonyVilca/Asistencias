from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models.usuario import Usuario
from app import db, login_manager


auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('asistencia.dashboard'))

    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        password = request.form['password']

        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
        if usuario and usuario.check_password(password) and usuario.estado:
            login_user(usuario)

            # 🔐 Verificamos si es el primer inicio
            if usuario.primer_inicio:
                flash("Bienvenido. Por seguridad debes cambiar tu contraseña.", "info")
                return redirect(url_for('auth.cambiar_contrasena'))

            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('asistencia.dashboard'))

        flash('Credenciales inválidas o usuario inactivo', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('auth.login'))

# 👇 Ruta adicional para cambiar contraseña en primer inicio
@auth_bp.route('/cambiar-contrasena', methods=['GET', 'POST'])
@login_required
def cambiar_contrasena():
    if not current_user.primer_inicio:
        flash("⚠️ Ya tienes una contraseña establecida.", "info")
        return redirect(url_for('asistencia.dashboard'))

    if request.method == 'POST':
        nueva = request.form['nueva']
        confirmar = request.form['confirmar']

        if len(nueva) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "warning")
        elif nueva != confirmar:
            flash("Las contraseñas no coinciden.", "warning")
        else:
            current_user.set_password(nueva)
            current_user.primer_inicio = False
            db.session.commit()
            flash("✅ Contraseña actualizada correctamente.", "success")
            return redirect(url_for('asistencia.dashboard'))

    return render_template('auth/cambiar_contrasena.html')
