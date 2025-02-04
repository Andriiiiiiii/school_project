# middlewares/throttling.py
from aiogram.dispatcher.middlewares import BaseMiddleware
import asyncio

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit=1):
        self.limit = limit
        super().__init__()

    async def on_process_message(self, message, data):
        await asyncio.sleep(0)  # Простая заглушка
