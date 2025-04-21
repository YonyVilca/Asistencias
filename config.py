class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://root:admin@localhost/asis"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "supersecretkey"  # cámbiala en producción
