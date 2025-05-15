from telegram.ext import Application
from bot_config import register_handlers

def main():
    app = Application.builder().token("7400853171:AAHZ5yw2iE9skXDRkel9TxrFS3eKfkGEMPg").build()
    register_handlers(app)
    print("✅ AI Helpdesk Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
