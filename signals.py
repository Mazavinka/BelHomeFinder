from playhouse.signals import post_save
from db import User, Post
from logger import logger
import asyncio
from typing import TYPE_CHECKING, Any


post_queue = asyncio.Queue()
user_queue = asyncio.Queue()


@post_save(sender=User)
def on_user_update(model_class, instance: User, created: bool) -> None:
    if not created and instance.is_active:
        safe_put(user_queue, instance)


@post_save(sender=Post)
def on_post_created(model_class, instance: User, created: bool) -> None:
    if created:
        safe_put(post_queue, instance)


def safe_put(queue: asyncio.Queue, item: Any) -> None:
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(queue.put(item))
    except RuntimeError:
        pass
    except Exception as e:
        logger.exception(f"Error queue: {e}")
