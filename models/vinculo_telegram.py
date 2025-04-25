from extensions import db
from datetime import datetime, timedelta

class VinculoTelegram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    codigo = db.Column(db.String(8), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Verifica si el token ha expirado (10 minutos)
    def expirado(self):
        return self.fecha_creacion + timedelta(minutes=10) < datetime.utcnow()
