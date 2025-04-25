from extensions import db

class IntentoFallido(db.Model):
    __tablename__ = 'intentos_fallidos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    ip = db.Column(db.String(50))
    razon = db.Column(db.Text)
    fecha_hora = db.Column(db.DateTime, server_default=db.func.now())
