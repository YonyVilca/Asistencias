from app import db


class Asistencia(db.Model):
    __tablename__ = 'asistencias'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora_entrada = db.Column(db.Time)
    hora_salida = db.Column(db.Time)
    ip = db.Column(db.String(50))
    observaciones = db.Column(db.Text)
    creado_en = db.Column(db.DateTime, server_default=db.func.now())
