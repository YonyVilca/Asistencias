from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import ContextTypes
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from extensions import db
from models.usuario import Usuario
from models.asistencia import Asistencia
from models.vinculo_telegram import VinculoTelegram
from datetime import datetime, date
from app import create_app
from datetime import datetime, date, time

serializer = URLSafeTimedSerializer("clave-secreta-muy-segura")

# /start y /menu → mostrar menú táctil según rol
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    telegram_id = str(update.effective_user.id)

    with app.app_context():
        usuario = Usuario.query.filter_by(telegram_id=telegram_id).first()
        if not usuario:
            await update.message.reply_text("❌ No estás vinculado a ninguna cuenta.")
            return

        if usuario.rol and usuario.rol.nombre == "admin":
            keyboard = [
                ["📋 Ver Usuarios", "📅 Resumen Día"],
                ["📊 Estado", "🔄 Desvincular"]
            ]
        else:
            keyboard = [["📲 Marcar Asistencia", "📊 Estado"]]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🙋‍♂️ ¡Bienvenido al sistema de asistencia!\nSelecciona una opción:",
            reply_markup=reply_markup
        )

# /estado o "📊 Estado" → resumen del día (sin entrada para admin)
async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    telegram_id = str(update.effective_user.id)

    with app.app_context():
        usuario = Usuario.query.filter_by(telegram_id=telegram_id).first()
        if not usuario:
            await update.message.reply_text("❌ No estás vinculado a ninguna cuenta.")
            return

        hoy = date.today()
        asistencias = Asistencia.query.filter_by(usuario_id=usuario.id, fecha=hoy).order_by(Asistencia.hora_entrada).all()

        entrada = asistencias[-1].hora_entrada.strftime('%H:%M') if asistencias and asistencias[-1].hora_entrada else "—"
        salida = asistencias[-1].hora_salida.strftime('%H:%M') if asistencias and asistencias[-1].hora_salida else "—"

        texto = f"""👤 *{usuario.nombres}*
📅 *Asistencia hoy:*
🟢 Entrada: `{entrada}`
🔴 Salida: `{salida}`"""

        keyboard = []
        if usuario.rol.nombre != "admin":
            if asistencias and asistencias[-1].hora_entrada and not asistencias[-1].hora_salida:
                keyboard.append([InlineKeyboardButton("🔒 Marcar Salida", callback_data=f"salida:{usuario.id}")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)

# Procesar texto del usuario (menú o código QR)
async def recibir_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    telegram_id = str(update.effective_user.id)

    app = create_app()

    # ✅ Rutas por botón
    if texto == "📊 Estado":
        await estado(update, context)
        return
    elif texto == "📲 Marcar Asistencia":
        await update.message.reply_text(
            "📸 Escanea tu código QR desde el panel web y pégalo aquí para registrar tu asistencia."
        )
        return
    elif texto == "📅 Resumen Día":
        await resumen_dia(update, context)
        return
    elif texto == "🔄 Desvincular":
        await desvincular(update, context)
        return
    elif texto == "📋 Ver Usuarios":
        await update.message.reply_text("⚠️ Esta opción está deshabilitada.")  # o llama a ver_usuarios(update, context)
        return

    # 🔐 Interpretar código QR pegado
    try:
        data = serializer.loads(texto, max_age=120)
        user_id = data.get("user_id")

        with app.app_context():
            usuario = Usuario.query.filter_by(id=user_id, telegram_id=telegram_id).first()
            if not usuario:
                await update.message.reply_text("❌ Este código QR no te pertenece.")
                return

            hoy = date.today()
            asistencias = Asistencia.query.filter_by(usuario_id=usuario.id, fecha=hoy).order_by(Asistencia.hora_entrada).all()
            entrada = asistencias[-1].hora_entrada.strftime('%H:%M') if asistencias and asistencias[-1].hora_entrada else "—"
            salida = asistencias[-1].hora_salida.strftime('%H:%M') if asistencias and asistencias[-1].hora_salida else "—"

            resumen = (
                f"📅 Asistencia hoy:\n"
                f"✅ Entrada: {entrada}\n"
                f"✅ Salida: {salida}\n\n"
                "¿Qué deseas hacer?"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🔓 Entrada", callback_data=f"entrada:{user_id}"),
                    InlineKeyboardButton("🔒 Salida", callback_data=f"salida:{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(resumen, reply_markup=reply_markup)

    except SignatureExpired:
        await update.message.reply_text("⚠️ El QR ha expirado.")
    except BadSignature:
        await update.message.reply_text("⚠️ El código QR es inválido.")


# Callback inline para botones de entrada/salida
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    action, user_id = query.data.split(":")

    from datetime import datetime, time, timedelta

    hora_minima_entrada = time(7, 55)
    hora_inicio = time(8, 0)
    tolerancia_entrada = timedelta(minutes=10)

    with app.app_context():
        usuario = Usuario.query.filter_by(id=user_id, telegram_id=telegram_id).first()
        if not usuario:
            await query.edit_message_text("❌ Acción no autorizada.")
            return

        hoy = date.today()
        ahora = datetime.now().time()
        asistencias = Asistencia.query.filter_by(usuario_id=usuario.id, fecha=hoy).order_by(Asistencia.hora_entrada).all()
        ultima = asistencias[-1] if asistencias else None

        if action == "entrada":
            if ultima and not ultima.hora_salida:
                await query.edit_message_text("⚠️ Ya tienes una entrada activa. Debes marcar salida primero.")
                return

            if ahora < hora_minima_entrada:
                await query.edit_message_text("❌ Solo puedes registrar entrada a partir de las 07:55 a.m.")
                return

            observacion = ""
            if ahora > (datetime.combine(hoy, hora_inicio) + tolerancia_entrada).time():
                observacion = "⏰ Tardanza"

            nueva = Asistencia(
                usuario_id=usuario.id,
                fecha=hoy,
                hora_entrada=ahora,
                observaciones=observacion or "Entrada por botón"
            )
            db.session.add(nueva)
            db.session.commit()

            mensaje = "🔓 Entrada registrada correctamente."
            if observacion:
                mensaje += " (Tardanza)"

            await query.edit_message_text(mensaje)

        elif action == "salida":
            if not ultima or ultima.hora_salida:
                await query.edit_message_text("⚠️ No tienes una entrada activa para marcar salida.")
                return

            ultima.hora_salida = ahora
            ultima.observaciones = ultima.observaciones or "Salida por botón"
            db.session.commit()

            await query.edit_message_text("🔒 Salida registrada correctamente.")


# /vincular <codigo>
async def vincular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    telegram_id = str(update.effective_user.id)

    if len(context.args) != 1:
        await update.message.reply_text("❌ Usa: /vincular ABC123")
        return

    codigo = context.args[0].strip().upper()
    with app.app_context():
        vinculo = VinculoTelegram.query.filter_by(codigo=codigo).first()
        if not vinculo:
            await update.message.reply_text("⚠️ El código no existe.")
            return
        if vinculo.expirado():
            await update.message.reply_text("⚠️ Código expirado.")
            db.session.delete(vinculo)
            db.session.commit()
            return

        usuario = Usuario.query.get(vinculo.usuario_id)
        if usuario.telegram_id:
            await update.message.reply_text("⚠️ Ya hay Telegram vinculado.")
            return

        usuario.telegram_id = telegram_id
        db.session.delete(vinculo)
        db.session.commit()
        await update.message.reply_text(f"✅ Vinculación exitosa, {usuario.nombres}.")

# /desvincular
async def desvincular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    telegram_id = str(update.effective_user.id)

    with app.app_context():
        usuario = Usuario.query.filter_by(telegram_id=telegram_id).first()

        if not usuario:
            await update.message.reply_text("❌ No estás vinculado a ninguna cuenta.")
            return

        usuario.telegram_id = None
        db.session.commit()
        await update.message.reply_text("🔓 Tu cuenta ha sido desvinculada exitosamente.")
# Ver resumen diario (para admin) con tabla formateada
# Vista mejorada para admins: resumen tipo tabla
async def resumen_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = create_app()
    telegram_id = str(update.effective_user.id)

    with app.app_context():
        usuario = Usuario.query.filter_by(telegram_id=telegram_id).first()
        if not usuario or usuario.rol.nombre != "admin":
            await update.message.reply_text("⛔ No autorizado.")
            return

        hoy = date.today()
        usuarios = Usuario.query.all()

        respuesta = "*📅 Resumen de Asistencia del Día*\n"
        respuesta += "`{:<18} {:<5} {:<5} {:<7} {:<7} {:<10}`\n".format(
            "Usuario", "Ent", "Sal", "Total", "Pend", "Estado"
        )
        respuesta += "`{:<18} {:<5} {:<5} {:<7} {:<7} {:<10}`\n".format(
            "-" * 18, "-" * 5, "-" * 5, "-" * 7, "-" * 7, "-" * 10
        )

        for u in usuarios:
            asistencias = Asistencia.query.filter_by(
                usuario_id=u.id, fecha=hoy
            ).order_by(Asistencia.hora_entrada).all()

            entrada = asistencias[-1].hora_entrada if asistencias and asistencias[-1].hora_entrada else None
            salida = asistencias[-1].hora_salida if asistencias and asistencias[-1].hora_salida else None

            entrada_str = entrada.strftime('%H:%M') if entrada else "—"
            salida_str = salida.strftime('%H:%M') if salida else "—"

            total = "—"
            pendiente = "09h00m"
            estado = "❌ Ausente"

            if entrada and salida:
                h_entrada = datetime.combine(hoy, entrada)
                h_salida = datetime.combine(hoy, salida)
                tiempo = h_salida - h_entrada
                total_seg = int(tiempo.total_seconds())
                h = total_seg // 3600
                m = (total_seg % 3600) // 60
                total = f"{h:02}h{m:02}m"

                esperado = 9 * 3600
                pendiente_seg = max(esperado - total_seg, 0)
                ph = pendiente_seg // 3600
                pm = (pendiente_seg % 3600) // 60
                pendiente = f"{ph:02}h{pm:02}m"

                if entrada <= time(8, 10):
                    estado = "✅ Puntual"
                else:
                    estado = "⏰ Tarde"

            elif entrada and not salida:
                estado = "🔄 Incompleto"

            respuesta += "`{:<18} {:<5} {:<5} {:<7} {:<7} {:<10}`\n".format(
                u.nombres[:18], entrada_str, salida_str, total, pendiente, estado
            )

        await update.message.reply_text(respuesta, parse_mode="Markdown")
