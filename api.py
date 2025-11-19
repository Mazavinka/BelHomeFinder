import aiohttp
import asyncio
from db import save_new_post_to_db, save_new_image_to_db
from logger import logger
from location import load_district_geojson, get_district_by_point, find_nearby, get_unique_nearby_objects
import signals

# ✅ Словарь городов (Kufar использует region code)
CITY_FILTERS = {
    "minsk": "country-belarus~province-minsk~locality-minsk",
    "vitebsk": "country-belarus~province-vitebskaja_oblast~area-vitebsk~locality-vitebsk",
    "gomel": "country-belarus~province-gomelskaja_oblast~locality-gomel",
    "grodno": "country-belarus~province-grodnenskaja_oblast~locality-grodno",
    "brest": "country-belarus~province-brestskaja_oblast~locality-brest",
    "mogilev": "country-belarus~province-mogilyovskaja_oblast~locality-mogilyov"
    }


async def fetch_ads(session, city, limit=30):
    city_filters = CITY_FILTERS.get(city.lower())
    if not city_filters:
        logger.error(f"Unknown city {city}")
        return None
    url = (
        f"https://api.kufar.by/search-api/v2/search/rendered-paginated"
        f"?cat=1010"
        f"&cur=BYR"
        f"&gtsy={city_filters}"
        f"&lang=ru"
        f"&size={limit}"
        f"&sort=lst.d"
        f"&typ=let"
    )

    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                logger.error(f"Error {resp.status} while send request to {url}")
                return None
    except asyncio.TimeoutError:
        logger.exception(f"Timeout to send request [{city}]")
    except Exception as e:
        logger.exception(f"Error to send request {e}")
    return None


def get_address(parameters):
    for parameter in parameters.get('account_parameters', []):
        if parameter.get('p') and parameter.get('p') == "address":
            return parameter.get('v')
    else:
        return "Без адреса"


def get_parameters(parameters):
    data = {'total_area': '', 'number_of_floors': '', 'balcony': '',
            'apartment_floor': '', 'number_of_rooms': '', 'prepayment': ''
            }

    for parameter in parameters.get('ad_parameters', []):
        parameter_name = parameter.get('pl', '')
        if parameter_name:
            if parameter_name == "Общая площадь":
                data['total_area'] = parameter.get('v', '')
            if parameter_name == "Комнат":
                data['number_of_rooms'] = parameter.get('vl', '')
            if parameter_name == "Этажность дома":
                data['number_of_floors'] = parameter.get('vl', '')
            if parameter_name == "Этаж":
                data['apartment_floor'] = parameter.get('vl')[0]
            if parameter_name == "Балкон":
                data['balcony'] = parameter.get('vl')
            if parameter_name == "Предоплата":
                data['prepayment'] = parameter.get('vl')

    return data


def get_location(parameters):
    for parameter in parameters.get('ad_parameters', []):
        if parameter.get('pl') and parameter.get('pl') == "Координаты":
            lon = parameter.get('v')[0]
            lat = parameter.get('v')[1]
            return lat, lon


async def parse_city(session, city):
    """Парсит конкретный город"""
    data = await fetch_ads(session, city)
    if not data or "ads" not in data:
        logger.error(f"No data to city: {city}")
        return

    for ad in data["ads"]:
        ad_id = str(ad.get("ad_id"))
        price_byn = price_to_float(ad.get("price_byn", 0.0))
        price_usd = price_to_float(ad.get("price_usd", 0.0))
        address = get_address(ad)
        short_description = ad.get("body_short", "Без описания")
        post_url = ad.get("ad_link", "")
        lat, lon = get_location(ad)
        city_district = str(get_district_by_point(lat, lon, load_district_geojson(city))).strip().lower() or ''

        nearby_obj = find_nearby(lat, lon, 1000)
        subway = ', '.join(get_unique_nearby_objects(nearby_obj.get('subway', []), 5)) if nearby_obj.get('subway') else ''
        pharmacy = ', '.join(get_unique_nearby_objects(nearby_obj.get('pharmacy', []), 5)) if nearby_obj.get('pharmacy') else ''
        kindergarten = ', '.join(get_unique_nearby_objects(nearby_obj.get('kindergarten', []), 5)) if nearby_obj.get('kindergarten') else ''
        school = ', '.join(get_unique_nearby_objects(nearby_obj.get('school', []), 5)) if nearby_obj.get('school') else ''
        bank = ', '.join(get_unique_nearby_objects(nearby_obj.get('bank', []), 5)) if nearby_obj.get('bank') else ''
        convenience = ', '.join(get_unique_nearby_objects(nearby_obj.get('convenience', []), 5)) if nearby_obj.get('convenience') else ''

        parameters = get_parameters(ad)
        rooms = parameters.get('number_of_rooms', '')
        number_of_floors = parameters.get('number_of_floors', '')
        apartment_floor = parameters.get('apartment_floor', '')
        total_area = parameters.get('total_area', '')
        balcony = parameters.get('balcony', '')
        prepayment = parameters.get('prepayment', '')




        saved = save_new_post_to_db(
            id=ad_id,
            price_byn=price_byn,
            price_usd=price_usd,
            address=address,
            short_description=short_description,
            post_url=post_url,
            city=city,
            lat=lat,
            lon=lon,
            city_district=city_district,
            subway=subway,
            pharmacy=pharmacy,
            kindergarten=kindergarten,
            school=school,
            bank=bank,
            shop=convenience,
            rooms=rooms,
            number_of_floors=number_of_floors,
            apartment_floor=apartment_floor,
            total_area=total_area,
            balcony=balcony,
            prepayment=prepayment

        )

        images = ad.get("images", "-")
        for img in images:
            if img:
                path = "https://rms.kufar.by/v1/list_thumbs_2x/" + img['path']
                save_new_image_to_db(path, ad_id)

        if saved:
            logger.info(f"New post [{ad_id}] for city {city}")


def price_to_float(price_):
    try:
        price = float(price_) / 100
        return price
    except ValueError:
        return price_


async def start_parse(interval=20):
    """Запускает парсер с заданным интервалом"""
    logger.info(f"Parser has been started")
    async with aiohttp.ClientSession() as session:
        while True:
            for city in CITY_FILTERS.keys():
                await parse_city(session, city)
                await asyncio.sleep(1)  # небольшая пауза между городами
            logger.info(f"Parsing complete. Waiting: {interval} sec...")
            await asyncio.sleep(interval)
