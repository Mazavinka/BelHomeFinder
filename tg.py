from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardMarkup, \
    KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
import asyncio
import os
from dotenv import load_dotenv
from db import get_or_create_user, get_user_by_id, get_districts_from_database
from messages import (start_message_text, min_price_text,
                      max_price_text, new_price_accepted,
                      need_number_text, city_text)
from logger import logger
from typing import Any
from models import Image, User


load_dotenv()

token = os.getenv('TG_BOT_TOKEN')
bot = Bot(token, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()

setting_messages = {}


class PriceRange(StatesGroup):
    waiting_for_min_price = State()
    waiting_for_max_price = State()


class CityAndDistrict(StatesGroup):
    waiting_for_city = State()
    waiting_for_district = State()


@dp.message(Command("start"))
async def command_start(message: Message) -> None:
    user, _ = await get_or_create_user(message.from_user.id, message.from_user.is_bot,
                                 message.from_user.first_name)
    await message.answer(start_message_text(message.from_user.first_name,
                                            user.city, user.min_price,
                                            user.max_price, user.is_active), reply_markup=add_button_settings())


@dp.message(F.text == "⚙️ Настройки ⚙️")
@dp.message(Command("settings"))
async def command_settings(message: Message) -> None:
    user, _ = await get_or_create_user(message.from_user.id, message.from_user.is_bot, message.from_user.first_name)
    user_id = message.from_user.id

    old_message_id = setting_messages.get(user_id)
    if old_message_id:
        try:
            await bot.delete_message(message.chat.id, old_message_id)
        except:
            pass

    msg = await message.answer("⚙️ Настройки ⚙️")
    setting_messages[user_id] = msg.message_id

    await render_settings_menu(user, msg)


async def render_settings_menu(user: User, message: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏙 Настроить город/район 🏙", callback_data="change_city")],
        [InlineKeyboardButton(text=f"💰 Настроить цену 💰", callback_data="change_price")],
        [InlineKeyboardButton(text=f"🚪 Количество комнат 🚪", callback_data="count_rooms")],

        [InlineKeyboardButton(text=f"🔔 Начать рассылку 🔔", callback_data="change_activity")] if not user.is_active
        else [InlineKeyboardButton(text=f"🔕 Остановить рассылку 🔕", callback_data="change_activity")]
    ])
    try:
        await message.edit_text("⚙️ *Настройки* ⚙️", reply_markup=kb)
    except TelegramBadRequest:
        await message.edit_reply_markup(reply_markup=kb)


@dp.callback_query(lambda c: c.data == "count_rooms")
async def change_rooms_menu(callback: CallbackQuery) -> None:
    user, _ = await get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)
    user_rooms_count = user.rooms_count
    kb = rooms_keyboard_set_state(user_rooms_count)
    await callback.message.edit_text("☑️ Выберите нужное количество комнат: ☑️", reply_markup=kb)


@dp.callback_query(lambda c: c.data.startswith('rooms_'))
async def choose_rooms(callback: CallbackQuery) -> None:
    user, _ = await get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)
    rooms_settings = int(callback.data.split('_', 1)[1])
    kb = rooms_keyboard_set_state(rooms_settings)

    try:
        await callback.message.edit_text("", reply_markup=kb)
    except TelegramBadRequest:
        await callback.message.edit_reply_markup(reply_markup=None)

    if user.rooms_count != rooms_settings:
        user.rooms_count = rooms_settings
        await user.save()
        await callback.message.edit_text("Ваш выбор успешно сохранён 💾")
    else:
        await callback.message.edit_text("У вас уже выбран этот вариант 👌")


@dp.callback_query(lambda c: c.data == "change_city")
async def choose_city(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CityAndDistrict.waiting_for_city)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌉 Брест 🌉", callback_data="city_brest")],
        [InlineKeyboardButton(text="🌆 Витебск 🌆", callback_data="city_vitebsk")],
        [InlineKeyboardButton(text="🏞 Гомель 🏞 ", callback_data="city_gomel")],
        [InlineKeyboardButton(text="🌿 Гродно 🌿", callback_data="city_grodno")],
        [InlineKeyboardButton(text="🏙 Минск 🏙", callback_data="city_minsk")],
        [InlineKeyboardButton(text="🌇 Могилёв 🌇", callback_data="city_mogilev")]
    ])

    setting_messages[callback.from_user.id] = callback.message.message_id

    await callback.message.edit_text(city_text(), reply_markup=kb)


@dp.callback_query(lambda c: c.data == "change_activity")
async def change_activity(callback: CallbackQuery) -> None:
    user, _ = await get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)
    if not user.is_active:
        user.is_active = True
        await user.save()
        await callback.message.edit_text(f"✅ Рассылка *включена*! Теперь я буду присылать тебе новые объявления 📩")
    else:
        user.is_active = False
        await user.save()
        await callback.message.edit_text(f"🚫 Рассылка *приостановлена*. Ты можешь включить её снова в любое время.")


@dp.callback_query(CityAndDistrict.waiting_for_city, F.data.startswith("city_"))
async def city_selected(callback: CallbackQuery, state: FSMContext) -> None:
    city = callback.data.split('_', 1)[1]

    await state.update_data(city=city)

    await state.set_state(CityAndDistrict.waiting_for_district)

    user, _ = await get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)

    districts = await get_districts_from_database(city)

    keyboard_with_districts = [[InlineKeyboardButton(text=district, callback_data=f"districts_{district}")] for district
                               in districts]
    keyboard_with_districts.append([InlineKeyboardButton(text="*Все районы*", callback_data="districts_all")])
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_with_districts)

    await callback.message.edit_text(f"✅ Город успешно изменён на *{city}*. Теперь выберите район: ", reply_markup=kb)


@dp.callback_query(CityAndDistrict.waiting_for_district, F.data.startswith("districts_"))
async def district_selected(callback: CallbackQuery, state: FSMContext) -> None:
    district = callback.data.split('_', 1)[1]
    data = await state.get_data()
    city = data['city']
    user, _ = await get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)
    user.city = city
    user.district = district
    await user.save()

    await state.clear()

    await callback.message.edit_text(f"Вы выбрали: {district}. В любой момент можете изменить свой выбор")
    await render_settings_menu(user, callback.message)


@dp.callback_query(lambda c: c.data == "change_price")
async def start_change_price(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(min_price_text())
    await state.set_state(PriceRange.waiting_for_min_price)


@dp.message(PriceRange.waiting_for_min_price)
async def set_min_price(message: Message, state: FSMContext) -> None:
    text = message.text.replace(" ", "").replace(',', '.')
    if not text.replace('.', '', 1).isdigit():
        await message.answer(need_number_text())
        return

    min_price = float(text)

    if min_price < 0:
        await message.answer("Цена не может быть отрицательной ❌")
        return

    await state.update_data(min_price=min_price)
    await message.answer(max_price_text())
    await state.set_state(PriceRange.waiting_for_max_price)


@dp.message(PriceRange.waiting_for_max_price)
async def set_max_price(message: Message, state: FSMContext) -> None:
    text = message.text.replace(' ', '').replace(',', '.')
    if not text.replace('.', '', 1).isdigit():
        await message.answer(need_number_text())
        return

    max_price = float(text)

    data = await state.get_data()
    min_price = data["min_price"]

    if max_price < min_price:
        await message.answer(f"⚠️ Максимальная цена должна быть больше минимальной.")
        return

    user, _ = await get_or_create_user(message.from_user.id, message.from_user.is_bot, message.from_user.first_name)
    user.min_price = min_price
    user.max_price = max_price
    await user.save()

    await state.clear()
    msg = await message.answer(new_price_accepted(min_price, max_price))
    await render_settings_menu(user, msg)


async def send_message_to_all(users_group: list[User], message: str) -> None:
    for user in users_group:
        user_id = user.id
        try:
            await bot.send_message(user_id, message)
        except Exception as e:
            logger.exception(f"Message to user [{user_id}] not sent: {e}")
        await asyncio.sleep(0.2)


async def message_to_new_user(user_id: str, message: str) -> bool:
    try:
        await bot.send_message(user_id, message)
    except Exception as e:
        logger.warning(f"Failed to send message to new user [{user_id}]: {e}")
        return False

    await asyncio.sleep(0.3)
    return True


async def start_bot():
    await dp.start_polling(bot)


async def send_post_with_images(user_id: str, images: list[Image], message: str) -> None:
    media = []
    for i, img in enumerate(images[:10]):
        if i == 0:
            media.append(InputMediaPhoto(media=images[i].image_src, caption=message, parse_mode='Markdown'))
        else:
            media.append(InputMediaPhoto(media=images[i].image_src))
    while True:
        try:
            await bot.send_media_group(chat_id=user_id, media=media)
            break
        except TelegramRetryAfter as e:
            logger.warning(f"FloodWait {e.retry_after} sec for user {user_id}")
            await asyncio.sleep(e.retry_after)
        except TelegramBadRequest as e:
            if "USER_IS_BLOCKED" in str(e):
                logger.info(f"User [{user_id}] was block bot")
                user = await get_user_by_id(user_id)
                user.is_active = False
                await user.save()
                return
            else:
                logger.exception(f"BadRequest for {user_id}: {e}")
                return
        except Exception as e:
            logger.exception(f"Error to send media group to user [{user_id}]: {e}")
            return
    await asyncio.sleep(1.5)


def add_button_settings() -> ReplyKeyboardMarkup:
    keyboard_with_settings = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Настройки ⚙️")]
        ],
        resize_keyboard=True
    )
    return keyboard_with_settings


def rooms_keyboard_set_state(rooms_count: int) -> InlineKeyboardMarkup:
    text_for_rooms_count = {1: "1 комната",
                            2: "2 комнаты",
                            3: "3 комнаты",
                            4: "4+ комнаты",
                            5: "Любое количество комнат",
                            }
    elements = []
    for key, value in text_for_rooms_count.items():
        if rooms_count == key:
            elements.append([InlineKeyboardButton(text=f"[ ✅ {value} ✅ ]", callback_data=f"rooms_{key}")])
        else:
            elements.append([InlineKeyboardButton(text=value, callback_data=f"rooms_{key}")])

    kb = InlineKeyboardMarkup(inline_keyboard=elements)
    return kb


if __name__ == "__main__":
    asyncio.run(start_bot())
