from playhouse.signals import post_save, post_delete
from db import User, Post
import asyncio

post_queue = asyncio.Queue()
user_queue = asyncio.Queue()


@post_save(sender=User)
def on_user_update(model_class, instance, created):
    if not created and instance.is_active:
        loop = asyncio.get_event_loop()
        loop.create_task(user_queue.put(instance))


@post_save(sender=Post)
def on_post_created(model_class, instance, created):
    if created:
        loop = asyncio.get_event_loop()
        loop.create_task(post_queue.put(instance))
