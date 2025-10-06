from config_reader import config
from ollama import summarize_news_list, ollama_answer
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode, ChatAction
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from qdrant import insert_documents, clear_collection, get_document_by_id, get_existing_titles, get_available_dates, get_documents_by_date, client, collection_name
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

async def background_clear_task():
    while True:
        await asyncio.sleep(43200)
        cleared = clear_collection()
        logging.info(f"Collection cleared: {cleared}")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Найти новость по номеру", callback_data="get_by_id")],
    [InlineKeyboardButton(text="Сводка по дням", callback_data="summary")]
])

class BotStates:
    WAIT_ID = "wait_id"
    WAIT_DATE = "wait_date"

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

    if data == "get_by_id":
        user_states[user_id] = BotStates.WAIT_ID
        await callback.message.answer("Введите номер документа:")
        await callback.answer()
    elif data == "summary":
        dates = get_available_dates()
        if not dates:
            await callback.message.answer("Нет доступных дат для сводки новостей. Возможно, сейчас обновляется список новостей, подождите 5 минут.", reply_markup=menu_kb)
        else:
            user_states[user_id] = BotStates.WAIT_DATE
            date_buttons = [
                [InlineKeyboardButton(text=date, callback_data=f"date_{date}")]
                for date in dates
            ]
            date_kb = InlineKeyboardMarkup(inline_keyboard=date_buttons)
            await callback.message.answer("Выберите дату сводки новостей:", reply_markup=date_kb)
        await callback.answer()
    
    elif data.startswith("date_") and user_states.get(user_id) == BotStates.WAIT_DATE:
        selected_date = data[len("date_"):]
        await callback.answer() 

        await callback.message.answer(f"Получаю новости за {selected_date} и формирую сводку...")

        points = get_documents_by_date(selected_date)
        if not points:
            await callback.message.answer(f"Новости за {selected_date} не найдены.", reply_markup=menu_kb)
            user_states.pop(user_id, None)
            return

        news_list = []
        for point in points:
            payload = point.payload or {}
            news_list.append({
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "source": payload.get("source", "")
            })

        summary = await summarize_news_list(news_list)
        await callback.message.answer(f"<b>Сводка новостей за {selected_date}:</b>\n\n{summary}", reply_markup=menu_kb)

        user_states.pop(user_id, None)

    else:
        await callback.answer()


@dp.message()
async def process_states(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == BotStates.WAIT_ID:
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
            source = payload.get("source", "Unknown")
            await message.answer(f"<b>Номер:</b> {doc_id}\n<b>Заголовок:</b> {title}\n<b>Содержимое:</b> {content}\n<b>Дата:</b> {date}\n<b>Источник:</b> {source}", reply_markup=menu_kb)
        user_states.pop(user_id, None)

    else:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        answer = await ollama_answer(message.text)
        await message.answer(f"{answer}")

if __name__ == "__main__":
    async def main():
        asyncio.create_task(background_parse_task())
        asyncio.create_task(background_clear_task())
        await dp.start_polling(bot)
    asyncio.run(main())