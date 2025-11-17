import aiohttp
import asyncio
from logger import logger


async def get_city_district(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=ru"
    if lat and lon:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(data['address']['city_district'])
                        return data['address']['city_district']
            except Exception as e:
                logger.error(f"Error to send request. {e}")
                return None
    else:
        logger.info("Coordinates not specified by user")
        return None



if __name__ == "__main__":
    asyncio.run(get_city_district(55.240959, 30.107863))
