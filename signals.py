from tortoise.signals import post_save
from models import User, Post
from logger import logger
import asyncio
from typing import Any, Type


post_queue = asyncio.Queue()
user_queue = asyncio.Queue()


@post_save(User)
async def on_user_update(sender: Type[User], instance: User, created: bool, using_db, update_fields) -> None:
    if not created and instance.is_active:
        safe_put(user_queue, instance)


"""@post_save(Post)
async def on_post_created(sender: Type[Post], instance: Post, created: bool, using_db, update_fields) -> None:
    if created:
        safe_put(post_queue, instance)"""


def safe_put(queue: asyncio.Queue, item: Any) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(queue.put(item))
    except RuntimeError:
        pass
    except Exception as e:
        logger.exception(f"Error queue: {e}")
