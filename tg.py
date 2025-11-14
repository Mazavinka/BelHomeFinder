from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.fsm.state import StatesGroup, State
import asyncio
import os
from dotenv import load_dotenv
from db import get_or_create_user, User
from messages import (start_message_text, min_price_text,
                      max_price_text, new_price_accepted,
                      need_number_text, city_text)
from logger import logger

load_dotenv()


token = os.getenv('TG_BOT_TOKEN')
bot = Bot(token)
dp = Dispatcher()


class PriceRange(StatesGroup):
    waiting_for_min_price = State()
    waiting_for_max_price = State()
    waiting_for_is_active = State()


@dp.message(Command("start"))
async def command_start(message):
    user, _ = get_or_create_user(message.from_user.id, message.from_user.is_bot,
                                 message.from_user.first_name)
    await message.answer(start_message_text(message.from_user.first_name,
                                            user.city, user.min_price,
                                            user.max_price, user.is_active), parse_mode="Markdown")
    await asyncio.sleep(1)
    await render_settings_menu(user, message)


@dp.message(Command("settings"))
async def command_settings(message):
    user, _ = get_or_create_user(message.from_user.id, message.from_user.is_bot,
                                 message.from_user.first_name)
    await render_settings_menu(user, message)


async def render_settings_menu(user, message):
    if not user.is_active:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏙 Настроить город 🏙", callback_data="change_city")],
            [InlineKeyboardButton(text=f"💰 Настроить цену 💰", callback_data="change_price")],
            [InlineKeyboardButton(text=f"🔔 Начать рассылку 🔔", callback_data="change_activity")]
        ])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏙 Настроить город 🏙", callback_data="change_city")],
            [InlineKeyboardButton(text=f"💰 Настроить цену 💰", callback_data="change_price")],
            [InlineKeyboardButton(text=f"🔕 Остановить рассылку 🔕", callback_data="change_activity")]
            ])
    await message.answer("⚙️ *Настройки* ⚙️", reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(lambda c: c.data == "change_city")
async def choose_city(callback):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌉 Брест 🌉", callback_data="city_brest")],
        [InlineKeyboardButton(text="🌆 Витебск 🌆", callback_data="city_vitebsk")],
        [InlineKeyboardButton(text="🏞 Гомель 🏞 ", callback_data="city_gomel")],
        [InlineKeyboardButton(text="🌿 Гродно 🌿", callback_data="city_grodno")],
        [InlineKeyboardButton(text="🏙 Минск 🏙", callback_data="city_minsk")],
        [InlineKeyboardButton(text="🌇 Могилёв 🌇", callback_data="city_mogilev")]
    ])

    await callback.message.edit_text(city_text(), reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(lambda c: c.data == "change_activity")
async def change_activity(callback):
    user, _ = get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)
    if not user.is_active:
        user.is_active = True
        user.save()
        await callback.message.edit_text(f"✅ Рассылка *включена*! Теперь я буду присылать тебе новые объявления 📩", parse_mode="Markdown")
    else:
        user.is_active = False
        user.save()
        await callback.message.edit_text(f"🚫 Рассылка *приостановлена*. Ты можешь включить её снова в любое время.", parse_mode="Markdown")
    await asyncio.sleep(1)
    # await render_settings_menu(user, callback.message)


@dp.callback_query(lambda c: c.data.startswith("city_"))
async def city_selected(callback):
    city = callback.data.split('_', 1)[1]
    user, _ = get_or_create_user(callback.from_user.id, callback.from_user.is_bot, callback.from_user.first_name)
    user.city = city
    user.save()
    await callback.message.edit_text(f"✅ Город успешно изменён на *{city}* 🏙", parse_mode="Markdown")
    await asyncio.sleep(1)

    await render_settings_menu(user, callback.message)


@dp.callback_query(lambda c: c.data == "change_price")
async def start_change_price(callback, state):
    await callback.message.edit_text(min_price_text(), parse_mode="Markdown")
    await state.set_state(PriceRange.waiting_for_min_price)


@dp.message(PriceRange.waiting_for_min_price)
async def set_min_price(message, state):
    try:
        min_price = float(message.text)
        await state.update_data(min_price=min_price)
        await message.answer(max_price_text(), parse_mode="Markdown")
        await state.set_state(PriceRange.waiting_for_max_price)
    except ValueError:
        logger.error(f"User type wrong symbols in min_price")
        await message.answer(need_number_text(), parse_mode="Markdown")


@dp.message(PriceRange.waiting_for_max_price)
async def set_max_price(message, state):
    try:
        price_max = float(message.text)
        data = await state.get_data()
        price_min = data['min_price']

        user, _ = get_or_create_user(message.from_user.id, message.from_user.is_bot, message.from_user.first_name)
        user.min_price = price_min
        user.max_price = price_max
        user.save()
        await state.clear()
        await message.answer(new_price_accepted(price_min, price_max), parse_mode="Markdown")
        await render_settings_menu(user, message)
    except ValueError:
        logger.error(f"User type wrong symbols in max_price")
        await message.answer(need_number_text(), parse_mode="Markdown")


async def send_message_to_all(users_group, message):
    for user in users_group:
        user_id = user.id
        try:
            await bot.send_message(user_id, message, parse_mode="Markdown")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.exception(f"Message to user [{user_id}] not send: {e}")
            await asyncio.sleep(0.5)


async def message_to_new_user(user_id, message):
    await bot.send_message(user_id, message, parse_mode="Markdown")
    await asyncio.sleep(1.1)


async def start_bot():
    await dp.start_polling(bot)


async def send_post_with_images(user_id, images, message):
    media = []
    if images:
        images_count = min(len(images), 10)  # max images 10!
        for i in range(images_count):
            if i == 0:
                media.append(InputMediaPhoto(media=images[i].image_src, caption=message, parse_mode="Markdown"))
            else:
                media.append(InputMediaPhoto(media=images[i].image_src))
        if not media:
            logger.warning(f"Error to send media to user [{user_id}]. Media is empty.")
        try:
            await bot.send_media_group(chat_id=user_id, media=media)
            await asyncio.sleep(1.1)
        except Exception as e:
            logger.exception(f"Error to send message to user [{user_id}]")


if __name__ == "__main__":
    asyncio.run(start_bot())
