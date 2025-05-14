from bot_handlers import start, handle_message
from telegram.ext import Application, CommandHandler, MessageHandler, filters

def main():
    app = Application.builder().token("7400853171:AAHZ5yw2iE9skXDRkel9TxrFS3eKfkGEMPg").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()