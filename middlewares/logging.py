# middlewares/logging.py
from aiogram.dispatcher.middlewares import BaseMiddleware
import logging

class LoggingMiddleware(BaseMiddleware):
    async def on_pre_process_update(self, update, data):
        logging.info(f"Received update: {update}")
