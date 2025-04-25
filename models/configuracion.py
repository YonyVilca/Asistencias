from extensions import db

class Configuracion(db.Model):
    __tablename__ = 'configuraciones'

    clave = db.Column(db.String(50), primary_key=True)
    valor = db.Column(db.Text)
