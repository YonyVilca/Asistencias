from app import db

class IPAutorizada(db.Model):
    __tablename__ = 'ips_autorizadas'

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activa = db.Column(db.Boolean, default=True)
