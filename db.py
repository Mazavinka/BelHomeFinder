import signals
from peewee import *
from datetime import datetime
from dotenv import load_dotenv
import os
from playhouse.signals import Model, post_save, post_delete


load_dotenv()

db = SqliteDatabase('database.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 64,
    'foreign_key': 1,
    'ignore_check_constraints': 0,
    'synchronous': 0
}, check_same_thread=False)


class Post(Model):
    id = CharField(primary_key=True, null=False, unique=True)
    price_byn = FloatField(default=0.0, null=True)
    price_usd = FloatField(default=0.0, null=True)
    parameters = TextField()
    address = TextField()
    short_description = CharField(max_length=150)
    post_url = TextField()
    date = DateTimeField(default=datetime.now)
    city = CharField(null=False)
    is_sent = BooleanField(null=False, default=False)

    class Meta:
        database = db


class User(Model):
    id = CharField(primary_key=True, null=False)
    is_bot = BooleanField(default=False)
    first_name = TextField()
    is_premium = BooleanField(default=False)

    min_price = FloatField()
    max_price = FloatField()
    city = CharField()
    is_active = BooleanField(default=False)

    class Meta:
        database = db


class Image(Model):
    id = AutoField(null=False)
    image_src = TextField(unique=True)
    loaded_to = CharField(default='/img')
    from_post = ForeignKeyField(Post, backref='images', on_delete='CASCADE')

    class Meta:
        database = db


def create_db():
    with db:
        db.create_tables([Post, User, Image])


def save_new_post_to_db(id, price_byn, price_usd, parameters, address, short_description, post_url, city):
    with db.atomic():
        new_post, created = Post.get_or_create(id=id, defaults={
            'price_byn': price_byn,
            'price_usd': price_usd,
            'parameters': parameters,
            'address': address,
            'short_description': short_description,
            'post_url': post_url,
            'city': city,
            'is_sent': False
        })
        if created:
            print(new_post, city)
            return True


def get_or_create_user(id, is_bot, first_name):
    new_user, created = User.get_or_create(id=id, defaults={
        'is_bot': is_bot,
        'first_name': first_name,
        'min_price': 1,
        'max_price': os.getenv('MAX_PRICE_UNLIMITED'),
        'city': 'vitebsk',
        'is_active': False,
    })

    return new_user, created


def save_new_image_to_db(src, post_id):
    if src and post_id:
        with db.atomic():
            new_image = Image.insert(image_src=src, from_post=post_id).on_conflict_ignore().execute()
        if new_image:
            print(new_image)
            return True


def get_last_five_posts(city, min_price, max_price, limit):
    last_posts = Post.select().where(
        (Post.city == city) &
        (Post.price_byn >= min_price) &
        (Post.price_byn <= max_price)).order_by(Post.date.desc()).limit(limit)
    return last_posts


def get_active_users(city):
    active_users = User.select().where((User.city == city) & (User.is_active == True))
    return active_users


if __name__ == "__main__":
    create_db()
