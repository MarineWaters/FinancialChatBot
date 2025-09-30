from config_reader import config
import ollama
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode, ChatAction
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from qdrant import insert_documents, search_documents, clear_collection, get_document_by_id, get_existing_titles, client, collection_name
from parser import parse_newest_pages

async def background_parse_task():
    while True:
        await asyncio.sleep(300)
        existing_titles = get_existing_titles()
        logging.info(f"Existing titles count: {len(existing_titles)}")
        new_docs = parse_newest_pages(stop_titles=existing_titles)
        if new_docs:
            inserted_count = insert_documents((new_docs))
            logging.info(f"Inserted {inserted_count} new parsed documents.")
        else:
            logging.info("No new documents found by parser.")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Search documents", callback_data="search")],
    [InlineKeyboardButton(text="Get by ID", callback_data="get_by_id")],
    [InlineKeyboardButton(text="Clear collection", callback_data="clear")]
])

class BotStates:
    WAIT_QUERY = "wait_query"
    WAIT_ID = "wait_id"

user_states = {}
user_temp_data = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот с поиском по документам в SmartLab.\nВыбери действие:",
        reply_markup=menu_kb
    )

@dp.callback_query()
async def callbacks_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data == "search":
        user_states[user_id] = BotStates.WAIT_QUERY
        await callback.message.answer("Введите документ для поиска похожих:")
        await callback.answer()
    elif data == "get_by_id":
        user_states[user_id] = BotStates.WAIT_ID
        await callback.message.answer("Введите ID документа (целое число):")
        await callback.answer()
    elif data == "clear":
        if clear_collection():
            await callback.message.answer("Коллекция очищена.")
        else:
            await callback.message.answer("Коллекция пустая или не существует.")
        await callback.answer()


@dp.message()
async def process_states(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == BotStates.WAIT_QUERY:
        query_text = message.text.strip()
        result_points = search_documents(query_text)
        if result_points is None:
            await message.answer("Коллекция пуста или не существует. Вставьте документы сначала.", reply_markup=menu_kb)
            user_states.pop(user_id, None)
            return
        if not result_points:
            await message.answer("Результаты не найдены.", reply_markup=menu_kb)
        else:
            text = "<b>Топ 3 подходящих документа:</b>\n\n"
            for point in result_points:
                payload = point.payload or {}
                title = payload.get("title", "Unknown")
                content = payload.get("content", "Unknown")
                date = payload.get("date", "Unknown")
                text += f"- Заголовок: {title}\n  Содержание: {content}\n Дата: {date}\n \n"
            await message.answer(text, reply_markup=menu_kb)
        user_states.pop(user_id, None)

    elif state == BotStates.WAIT_ID:
        try:
            doc_id = int(message.text.strip())
        except ValueError:
            await message.answer("Недопустимый ID. Пожалуйста, введите целое число.")
            return
        point = get_document_by_id(doc_id)
        if point is None:
            await message.answer(f"Документ с ID {doc_id} не найден или коллекция пуста.", reply_markup=menu_kb)
        else:
            payload = point.payload or {}
            title = payload.get("title", "Unknown")
            content = payload.get("content", "Unknown")
            date = payload.get("date", "Unknown")
            await message.answer(f"<b>Document ID:</b> {doc_id}\n<b>Title:</b> {title}\n<b>Content:</b> {content}\n<b>Date:</b> {date}", reply_markup=menu_kb)
        user_states.pop(user_id, None)

    else:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        answer = await ollama.OllamaAnswer(message.text)
        await message.answer(f"{answer}")

if __name__ == "__main__":
    async def main():
        asyncio.create_task(background_parse_task())
        await dp.start_polling(bot)
    asyncio.run(main())