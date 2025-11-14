import aiohttp
import asyncio
from db import save_new_post_to_db, save_new_image_to_db
from logger import  logger
from messages import post_text
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
        async with session.get(url, timeout=20) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                logger.error(f"Error {resp.status} while send request to {url}")
                return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout to send request [{city}]")
    except Exception as e:
        logger.error(f"Error to send request {e}")
    return None


def get_address(parameters):
    for parameter in parameters['account_parameters']:
        if parameter.get('p') and parameter.get('p') == "address":
            return parameter.get('v')
    else:
        return "Без адреса"


def get_parameters(parameters):
    data = []
    for parameter in parameters['ad_parameters']:
        if parameter.get('pl') and parameter.get('pl') == "Общая площадь":
            data.append(f"Общая площадь: {parameter.get('v')} кв.м. ")
        elif parameter.get('pl') and parameter.get('pl') == "Комнат":
            data.append(f"Количество комнат: {parameter.get('vl')}. ")
        elif parameter.get('pl') and parameter.get('pl') == "Этажность дома":
            data.append(f"Этажность дома: {parameter.get('vl')}. ")
        elif parameter.get('pl') and parameter.get('pl') == "Этаж":
            data.append(f"Этаж: {parameter.get('vl')[0]}. ")
        elif parameter.get('pl') and parameter.get('pl') == "Балкон":
            data.append(f"Балкон: {parameter.get('vl')}. ")
        elif parameter.get('pl') and parameter.get('pl') == "Предоплата":
            data.append(f"Предоплата: {parameter.get('vl')}. ")
    return "".join(data)


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
        parameters = get_parameters(ad)

        saved = save_new_post_to_db(
            id=ad_id,
            price_byn=price_byn,
            price_usd=price_usd,
            parameters=parameters,
            address=address,
            short_description=short_description,
            post_url=post_url,
            city=city
        )

        images = ad.get("images", "-")
        for img in images:
            print(img)
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
