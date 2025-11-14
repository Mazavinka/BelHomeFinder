from playhouse.signals import post_save
from db import User, Post
from logger import logger
import asyncio

post_queue = asyncio.Queue()
user_queue = asyncio.Queue()


@post_save(sender=User)
def on_user_update(model_class, instance, created):
    if not created and instance.is_active:
        safe_put(user_queue, instance)


@post_save(sender=Post)
def on_post_created(model_class, instance, created):
    if created:
        safe_put(post_queue, instance)


def safe_put(queue, item):
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(queue.put(item))
    except RuntimeError:
        pass
    except Exception as e:
        logger.error(f"Error queue: {e}")
