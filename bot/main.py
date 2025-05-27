import os
import uuid
import asyncio
import httpx
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import Column, String, create_engine, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7475775010:AAHSJQd-PX4nJYC22anBl7RW9XQnpleXggg")
API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
DATABASE_URL = os.getenv("SQLITE_DB_PATH", "sqlite:///bot.sqlite")

if not BOT_TOKEN:
    raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

# Настройка SQLAlchemy
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class UserThread(Base):
    __tablename__ = "threads"
    chat_id = Column(String, primary_key=True, index=True)
    thread_id = Column(UUID)

Base.metadata.create_all(bind=engine)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_thread_id(chat_id: int) -> uuid.UUID:
    session = SessionLocal()
    try:
        record = session.query(UserThread).filter(UserThread.chat_id == str(chat_id)).first()
        return record.thread_id if record else None
    finally:
        session.close()

async def set_thread_id(chat_id: int, thread_id: uuid.UUID):
    session = SessionLocal()
    try:
        record = session.query(UserThread).filter(UserThread.chat_id == str(chat_id)).first()
        if record:
            record.thread_id = thread_id
        else:
            record = UserThread(chat_id=str(chat_id), thread_id=thread_id)
            session.add(record)
        session.commit()
    finally:
        session.close()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я телеграм-бот для общения с RAG API.\n"
        "Просто отправь любое сообщение, и я передам его в API.\n"
        "Команда /reset сбросит контекст диалога."
    )

@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    chat_id = message.chat.id
    await set_thread_id(chat_id, uuid.uuid4())
    await message.answer("Контекст диалога сброшен.")

@dp.message()
async def handle_message(message: Message):
    chat_id = message.chat.id
    question = message.text.strip()
    if not question:
        return

    thread_id = await get_thread_id(chat_id)
    if not thread_id:
        thread_id = str(uuid.uuid4())
        await set_thread_id(chat_id, thread_id)
    request_id = str(uuid.uuid4())
    payload = {"id": request_id, "question": question, "thread_id": str(thread_id)}

    async with httpx.AsyncClient() as client:
        try:
            url = f"{API_URL}/bot/chat?chat_id={chat_id}"
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return await message.answer(f"HTTP ошибка: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            return await message.answer(f"Ошибка при запросе к API: {e}")

    data = response.json()
    answer = data.get("answer", "")

    await message.answer(answer)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
