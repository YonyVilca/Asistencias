import os
from app import create_app
from extensions import db
from models.asistencia import Asistencia
from datetime import datetime, date, time

def marcar_auto_salidas():
    app = create_app()
    with app.app_context():
        hoy = date.today()
        ahora = datetime.now()

        asistencias_abiertas = Asistencia.query.filter(
            Asistencia.fecha == hoy,
            Asistencia.hora_entrada.isnot(None),
            Asistencia.hora_salida.is_(None)
        ).all()

        for asistencia in asistencias_abiertas:
            asistencia.hora_salida = time(18, 0)
            if asistencia.observaciones:
                asistencia.observaciones += " | 🚪 Auto-salida (olvidó marcar)"
            else:
                asistencia.observaciones = "🚪 Auto-salida (olvidó marcar)"
            print(f"Auto-salida marcada para usuario {asistencia.usuario_id}.")

        db.session.commit()
        print("✅ Auto-salidas registradas correctamente.")

if __name__ == "__main__":
    marcar_auto_salidas()
