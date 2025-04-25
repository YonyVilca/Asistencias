# al inicio
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    rol = db.relationship('Rol', backref='usuarios')
    estado = db.Column(db.Boolean, default=True)
    primer_inicio = db.Column(db.Boolean, default=True)
    eliminado = db.Column(db.Boolean, default=False)  # 🗑️ Eliminación lógica
    fecha_registro = db.Column(db.DateTime, server_default=db.func.now())
    telegram_id = db.Column(db.String(100))  # 🔥 AGREGA ESTA LÍNEA
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 👇 Agregar esta parte AL FINAL DEL ARCHIVO
from .asistencia import Asistencia
Usuario.asistencias = db.relationship(Asistencia, backref='usuario', lazy=True)
