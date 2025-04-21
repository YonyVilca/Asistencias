from datetime import datetime, time
from app import create_app, db
from models.asistencia import Asistencia

app = create_app()
with app.app_context():
    hoy = datetime.today().date()
    hora_auto_salida = time(17, 10)

    asistencias_pendientes = Asistencia.query.filter(
        Asistencia.fecha == hoy,
        Asistencia.hora_entrada.isnot(None),
        Asistencia.hora_salida.is_(None)
    ).all()

    for asistencia in asistencias_pendientes:
        asistencia.hora_salida = hora_auto_salida
        observacion = asistencia.observaciones or ""
        if "No marcó salida" not in observacion:
            asistencia.observaciones = (observacion + " ⚠️ No marcó salida").strip()

    db.session.commit()
    print(f"✅ Se asignó salida automática a {len(asistencias_pendientes)} usuarios.")
