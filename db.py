import signals
from peewee import *
from datetime import datetime
from dotenv import load_dotenv
import os
from playhouse.migrate import *
from playhouse.signals import Model
from logger import logger

load_dotenv()

db = SqliteDatabase(os.getenv("DB_PATH"), pragmas={
    'journal_mode': 'delete',
    'cache_size': -1024 * 64,
    'foreign_keys': 1,
    'ignore_check_constraints': 0,
    'synchronous': 1
}, check_same_thread=False)


class BaseModel(Model):
    class Meta:
        database = db


class Post(BaseModel):
    id = CharField(primary_key=True, null=False, unique=True)
    price_byn = FloatField(default=0.0, null=True)
    price_usd = FloatField(default=0.0, null=True)
    address = TextField()
    short_description = CharField(max_length=150)
    post_url = TextField()
    date = DateTimeField(default=datetime.now)
    city = CharField(null=False)
    is_sent = BooleanField(null=False, default=False)
    lat = FloatField(null=True)
    lon = FloatField(null=True)
    city_district = CharField(null=True)

    nearby_subway = CharField(null=True, default='')
    nearby_pharmacy = CharField(null=True, default='')
    nearby_kindergarten = CharField(null=True, default='')
    nearby_school = CharField(null=True, default='')
    nearby_bank = CharField(null=True, default='')
    nearby_shop = CharField(null=True, default='')

    rooms = CharField(null=True, default='')
    number_of_floors = CharField(null=True, default='')
    apartment_floor = CharField(null=True, default='')
    total_area = CharField(null=True, default='')
    balcony = CharField(null=True, default='')
    prepayment = CharField(null=True, default='')


class User(BaseModel):
    id = CharField(primary_key=True, null=False)
    is_bot = BooleanField(default=False)
    first_name = TextField()
    is_premium = BooleanField(default=False)

    min_price = FloatField()
    max_price = FloatField()
    city = CharField()
    district = CharField()
    is_active = BooleanField(default=False)
    rooms_count = IntegerField(default=5)


class Image(BaseModel):
    id = AutoField(null=False)
    image_src = TextField(unique=True)
    loaded_to = CharField(default='/img')
    from_post = ForeignKeyField(Post, backref='images', on_delete='CASCADE')


def create_db():
    try:
        with db:
            db.create_tables([Post, User, Image], safe=True)
    except (OperationalError, ProgrammingError) as e:
        logger.exception(f"Failed to create database tables: {e}")


def save_new_post_to_db(id, price_byn, price_usd, address, short_description,
                        post_url, city, lat, lon, city_district, subway, pharmacy, kindergarten, school, bank, shop,
                        rooms, number_of_floors, apartment_floor, total_area, balcony, prepayment):
    try:
        with db.atomic():
            new_post, created = Post.get_or_create(id=id, defaults={
                'price_byn': price_byn,
                'price_usd': price_usd,
                'address': address,
                'short_description': short_description,
                'post_url': post_url,
                'city': city,
                'is_sent': False,
                'lat': lat,
                'lon': lon,
                'city_district': city_district,
                'nearby_subway': subway,
                'nearby_pharmacy': pharmacy,
                'nearby_kindergarten': kindergarten,
                'nearby_school': school,
                'nearby_bank': bank,
                'nearby_shop': shop,
                'rooms': rooms,
                'number_of_floors': number_of_floors,
                'apartment_floor': apartment_floor,
                'total_area': total_area,
                'balcony': balcony,
                'prepayment': prepayment,
            })
            if created:
                logger.info(f"The new record has been successfully added to database. ID: [{id}]")
                return True
            return False
    except Exception as e:
        logger.exception(f"Error saving recor to database. ID: [{id}]. {e}")


def get_or_create_user(id, is_bot, first_name):
    try:
        new_user, created = User.get_or_create(id=id, defaults={
            'is_bot': is_bot,
            'first_name': first_name,
            'min_price': 1,
            'max_price': float(os.getenv('MAX_PRICE_UNLIMITED')),
            'city': 'vitebsk',
            'is_active': False,
            'district': 'all',
            'rooms_count': 5,
        })
        return new_user, created
    except (OperationalError, IntegrityError) as e:
        logger.exception(f"Error creating or getting user [{id}]: {e}")


def save_new_image_to_db(src, post_id):
    if not src or not post_id:
        return False

    try:
        with db.atomic():
            new_image = Image.insert(image_src=src, from_post=post_id).on_conflict_ignore().execute()
        if new_image:
            return True
    except (OperationalError, IntegrityError) as e:
        logger.exception(f"Failed to save image for post [{post_id}]")
        return False


def get_user_by_id(user_id):
    try:
        user = User.get(User.id == user_id)
        return user
    except Exception as e:
        logger.exception(f"Error. Can't found User with id: [{user_id}]. {e}")


def get_last_five_posts(city, min_price, max_price, limit, district, rooms_count):
    try:
        district = str(district).strip().lower()
        min_price = float(min_price)
        max_price = float(max_price)
        last_posts = Post.select().where(
            (Post.city == city) &
            (Post.price_byn >= min_price) &
            (Post.price_byn <= max_price)).order_by(Post.date.desc())
        last_posts = rooms_count_filter_posts(rooms_count, last_posts)
        if district and district != "all":
            last_posts = last_posts.where(Post.city_district == district)
        return last_posts.limit(limit)
    except (OperationalError, DataError, ValueError) as e:
        logger.exception(f"Failed to get posts for city [{city}]: {e}")
        return []


def get_active_users(city, district, rooms_count):
    try:
        city = str(city)
        active_users = User.select().where((User.city == city) & (User.is_active == True) &
                                           ((User.district == "all") | (User.district == district)))
        active_users = rooms_count_filter_users(rooms_count, active_users)
        return active_users
    except (OperationalError, DataError, ValueError) as e:
        logger.exception(f"Failed to get active users for city [{city}]: {e}")
        return []


def rooms_count_filter_users(rooms_count, users):
    if rooms_count in [1, 2, 3]:
        return users.where(User.rooms_count == rooms_count)
    elif rooms_count == 4:
        return users.where(User.rooms_count >= rooms_count)
    else:
        return users


def rooms_count_filter_posts(rooms_count, posts):
    if rooms_count in [1, 2, 3]:
        return posts.where(Post.rooms == rooms_count)
    elif rooms_count == 4:
        return posts.where(Post.rooms >= rooms_count)
    else:
        return posts


def get_districts_from_database(city):
    city = str(city).strip().lower()
    data = {"minsk": [], "vitebsk": [], "grodno": [], "mogilev": [], "gomel": [], "brest": []}
    for post in Post.select():
        if post.city_district not in data[post.city]:
            data[post.city].append(str(post.city_district).strip().lower())
    return data[city]


def add_column_to_table(model_name, new_column, field_type,  db=db):
    migrator = SqliteMigrator(db)
    migrate(
        migrator.add_column(model_name, new_column, field_type)
    )


def drop_column_from_table(model_name, column):
    migrator = SqliteMigrator(db)
    migrate(
        migrator.drop_column(model_name, column)
    )


if __name__ == "__main__":
    create_db()
