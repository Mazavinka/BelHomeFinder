from models import User, Post, Image
from logger import logger
import os
from typing import Any
from tortoise.exceptions import IntegrityError, OperationalError, DoesNotExist
from tortoise.queryset import QuerySet
from tortoise.expressions import Q
from tortoise import Tortoise
from dotenv import load_dotenv

load_dotenv()

TORTOISE_ORM = {
    "connections": {
        "default": os.getenv("DB_PATH"),
    },
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        }
    }
}


async def save_new_post_to_db(id: str,
                              price_byn: float,
                              price_usd: float,
                              address: str,
                              short_description: str,
                              post_url: str,
                              city: str,
                              lat: float,
                              lon: float,
                              city_district: str,
                              subway: str,
                              pharmacy: str,
                              kindergarten: str,
                              school: str,
                              bank: str,
                              shop: str,
                              rooms: str,
                              number_of_floors: str,
                              apartment_floor: str,
                              total_area: str,
                              balcony: str,
                              prepayment: str) -> bool:
    try:
        new_post, created = await Post.get_or_create(
            id=id, defaults={
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
    except IntegrityError:
        logger.info(f"Post{id} already exists")
    except Exception as e:
        logger.exception(f"Error saving recor to database. ID: [{id}]. {e}")


async def get_or_create_user(id: int, is_bot: bool, first_name: str) -> tuple[Any, Any]:
    try:
        new_user, created = await User.get_or_create(id=id, defaults={
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
        return None, False


async def save_new_image_to_db(src: str, post_id: str) -> bool:
    if not src or not post_id:
        return False

    try:
        post = await Post.get(id=post_id)
    except DoesNotExist as e:
        logger.exception(f"Skip image, post [{post_id}] does not exist")
        return False

    try:
        await Image.get_or_create(image_src=src, defaults={"from_post": post})
        return True
    except Exception as e:
        logger.exception(f"Failed to save image for post [{post_id}] -> {e}")
        return False



async def get_user_by_id(user_id: str) -> User:
    try:
        return await User.get(User.id == user_id)
    except DoesNotExist:
        logger.warning(f"User with id {user_id} not found")
    except Exception as e:
        logger.exception(f"Error. Can't found User with id: [{user_id}]. {e}")


async def get_last_five_posts(city: str, min_price: float, max_price: float, limit: int, district: str,
                              rooms_count: int) -> list[Post]:
    try:
        district = str(district).strip().lower()
        min_price = min_price
        max_price = max_price
        last_posts = Post.filter(city=city, price_byn__gte=min_price, price_byn__lte=max_price)
        last_posts = rooms_count_filter_posts(rooms_count, last_posts)
        if district and district != "all":
            last_posts = last_posts.filter(city_district=district)
        return await last_posts.order_by("-date").limit(limit)
    except Exception as e:
        logger.exception(f"Failed to get posts for city [{city}]: {e}")
        return []


def rooms_count_filter_users(rooms_count: int, users: QuerySet[User]) -> QuerySet[User]:
    if rooms_count in [1, 2, 3]:
        return users.filter(rooms_count=rooms_count)
    elif rooms_count == 4:
        return users.filter(rooms_count__gte=4)
    else:
        return users


def rooms_count_filter_posts(rooms_count: int, posts: QuerySet[Post]) -> QuerySet[Post]:
    if rooms_count in [1, 2, 3]:
        return posts.filter(rooms=rooms_count)
    elif rooms_count == 4:
        return posts.filter(rooms__gte=4)
    else:
        return posts


async def get_districts_from_database(city: str) -> list:
    city = str(city).strip().lower()
    data = {"minsk": [], "vitebsk": [], "grodno": [], "mogilev": [], "gomel": [], "brest": []}
    districts = await Post.filter(city=city).exclude(city_district__isnull=True).exclude(
        city_district="").distinct().values_list("city_district", flat=True)

    for d in districts:
        data[city].append(d.strip().lower())
    return data[city]


async def get_active_users(city: str, district: str, rooms_count: int) -> QuerySet[User]:
    try:
        return rooms_count_filter_users(rooms_count,
                                        User.filter(
                                            Q(city=city),
                                            Q(is_active=True),
                                            Q(district="all") | Q(district=district)
                                        ))
    except Exception as e:
        logger.exception(f"Failed to get active users for city [{city}]: {e}")
        return User.filter(id=0)


async def init_db():
    await Tortoise.init(
        db_url=os.getenv("DB_PATH"),
        modules={"models": ["models"]}
    )

    await Tortoise.generate_schemas(safe=True)
