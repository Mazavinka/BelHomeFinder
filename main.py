import asyncio
import signals
from db import get_last_five_posts, get_active_users, init_db
from tg import start_bot, message_to_new_user, send_message_to_all, send_post_with_images
from api import start_parse
from messages import post_text
from models import User, Post
from logger import logger


async def handle_new_post():
    while True:
        new_post = await signals.post_queue.get()
        try:
            asyncio.create_task(send_new_post_to_users(new_post.city, new_post))
        except Exception as e:
            logger.warning(f"Error is handler: {e}")


async def handle_new_is_active_users():
    while True:
        new_user = await signals.user_queue.get()
        asyncio.create_task(send_posts_for_new_user(new_user))


async def send_new_post_to_users(city: str, post: Post) -> None:
    active_users_qs = await get_active_users(city, post.city_district, post.rooms)
    active_users = await active_users_qs

    users_with_true_price_filters = [user for user in active_users if user.min_price <= post.price_byn <= user.max_price]

    images = await post.images.all()

    if not post.is_sent:
        if images:
            for user in users_with_true_price_filters:
                await send_post_with_images(user.id, images, post_text(post))
        else:
            await send_message_to_all(users_with_true_price_filters, post_text(post))
        post.is_sent = True
        await post.save()


async def send_posts_for_new_user(new_user: User) -> None:
    posts = await get_last_five_posts(new_user.city, new_user.min_price, new_user.max_price, 5, new_user.district, new_user.rooms_count)
    for post in posts:
        images = await post.images.all()
        if images:
            await send_post_with_images(new_user.id, images, post_text(post))
        else:
            await message_to_new_user(new_user.id, post_text(post))


async def run(interval):
    await init_db()

    asyncio.create_task(start_parse(interval))
    asyncio.create_task(handle_new_post())
    asyncio.create_task(handle_new_is_active_users())

    await start_bot()

if __name__ == "__main__":
    asyncio.run(run(interval=10 * 60))
