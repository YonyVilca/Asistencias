from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)
from dotenv import load_dotenv
import os

# Importa tus funciones del bot
from bot_handler import (
    start, estado, recibir_token,
    callback_handler, vincular, desvincular
)

# Carga token desde .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# ✅ Crea la aplicación del bot
app = Application.builder().token(TOKEN).build()

# === Handlers ===
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", start))
app.add_handler(CommandHandler("estado", estado))
app.add_handler(CommandHandler("vincular", vincular))
app.add_handler(CommandHandler("desvincular", desvincular))
from bot_handler import resumen_dia
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_token))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(CommandHandler("resumen_dia", resumen_dia))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📅 Resumen Día$"), resumen_dia))
# ✅ Inicia el bot
if __name__ == "__main__":
    print("🤖 Bot iniciado. Esperando mensajes...")
    app.run_polling()


