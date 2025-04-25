from flask import Blueprint, request, abort, send_file
from flask_login import login_required, current_user
from itsdangerous import URLSafeTimedSerializer
from io import BytesIO
import qrcode
from models.ip_autorizada import IPAutorizada

qr_bp = Blueprint('qr', __name__)
serializer = URLSafeTimedSerializer("clave-secreta-muy-segura")

@qr_bp.route('/generar_qr')
@login_required
def generar_qr():
    # 🔐 Bloqueo por IP
    ip = request.remote_addr
    ip_autorizada = IPAutorizada.query.filter_by(ip=ip, activa=True).first()

    if not ip_autorizada:
        abort(403, description="⛔ No está autorizada para generar el código QR.")

    # 🧾 Generar token con expiración
    token = serializer.dumps({'user_id': current_user.id})

    # 📸 Generar imagen QR
    qr = qrcode.make(token)
    img_io = BytesIO()
    qr.save(img_io, format='PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')
