import asyncio
import signals
from db import get_last_five_posts, get_active_users
from tg import start_bot, message_to_new_user, send_message_to_all, send_post_with_images
from kufar_api import start_parse
from messages import post_text


async def handle_new_post():
    while True:
        new_post = await signals.post_queue.get()
        asyncio.create_task(send_new_post_to_users(new_post.city, new_post))


async def handle_new_is_active_users():
    while True:
        new_user = await signals.user_queue.get()
        asyncio.create_task(send_posts_for_new_user(new_user))


async def send_new_post_to_users(city, post):
    active_users = get_active_users(city)
    users_with_true_price_filters = [user for user in active_users if user.min_price <= post.price_byn <= user.max_price]
    if not post.is_sent:
        if post.images:
            for user in users_with_true_price_filters:
                await send_post_with_images(user.id, post.images, post_text(post))
        else:
            await send_message_to_all(users_with_true_price_filters, post_text(post))
        post.is_sent = True
        post.save()


async def send_posts_for_new_user(new_user):
    posts = get_last_five_posts(new_user.city, new_user.min_price, new_user.max_price, 5)
    for post in posts:
        if post.images:
            await send_post_with_images(new_user.id, post.images, post_text(post))
        else:
            await message_to_new_user(new_user.id, post_text(post))


async def run(interval):
    await asyncio.gather(
        start_parse(interval),
        start_bot(),
        handle_new_post(),
        handle_new_is_active_users()
    )


if __name__ == "__main__":
    asyncio.run(run(interval=10 * 60))
