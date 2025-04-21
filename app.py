from flask import Flask
from config import Config
from extensions import db, login_manager
from datetime import datetime, timedelta

def todatetime(t):
    return datetime.combine(datetime.today(), t) if t else None

def horas_minutos(td):
    if not td or not isinstance(td, timedelta):
        return "-"
    total_minutes = int(td.total_seconds() // 60)
    horas = total_minutes // 60
    minutos = total_minutes % 60
    return f"{horas:02}:{minutos:02}"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Importaciones internas
    from models.usuario import Usuario
    from models import usuario, rol, asistencia, horario, intento_fallido, ip_autorizada, configuracion
    from routes.auth import auth_bp
    from routes.asistencia import asistencia_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(asistencia_bp)
    app.register_blueprint(admin_bp)

    # Filtros Jinja personalizados
    app.jinja_env.filters['todatetime'] = todatetime
    app.jinja_env.filters['horas_minutos'] = horas_minutos

    with app.app_context():
        db.create_all()

        # Crear roles iniciales
        from models.rol import Rol
        roles_iniciales = ['admin', 'empleado']
        for nombre in roles_iniciales:
            if not Rol.query.filter_by(nombre=nombre).first():
                nuevo_rol = Rol(nombre=nombre, descripcion=f'Rol {nombre}')
                db.session.add(nuevo_rol)
        db.session.commit()

    return app

# Ejecutar en modo desarrollo
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
