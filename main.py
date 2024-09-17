from telegram_bot import telegram_bot
from components.routes import fastapi_main

# main program, choose between fastapi and telegram, only 1 can run at a time
if __name__ == "__main__":
    fastapi_main()
    # telegram_bot()