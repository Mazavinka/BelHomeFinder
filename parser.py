import asyncio
import hashlib
import os
import random
import aiohttp
from bs4 import BeautifulSoup
from headers import my_headers
from dotenv import load_dotenv
from db import save_new_post_to_db, save_new_image_to_db

load_dotenv()


class Parser:
    def __init__(self, city):
        self.city = city
        self.selector_price_byn = 'span[class*="styles_price__byr"]'
        self.selector_price_usd = '[class*="styles_price__usd"]'
        self.selector_parameters = '[class*="styles_parameters"]'
        self.selector_address = 'span[class*="styles_address"]'
        self.selector_short_description = '[class*="styles_body"]'
        self.selector_post_url = 'a[data-testid*="kufar-realty-card"]'
        self.selector_post_id = 'a[data-testid*="kufar-realty-card"]'

    def get_starting_url(self):
        url = os.getenv('STARTING_URL').replace('city', self.city)
        return url

    async def get_all_posts_from_page(self, bs_object):
        all_posts = bs_object.select('section')
        for post in all_posts:
            price_byn = set_clean_byn_price(safe_text_from_post(post, self.selector_price_byn))
            price_usd = set_clean_usd_price(safe_text_from_post(post, self.selector_price_usd))
            parameters = safe_text_from_post(post, self.selector_parameters)
            address = safe_text_from_post(post, self.selector_address)
            short_description = safe_text_from_post(post, self.selector_short_description)
            post_url = safe_url_from_post(post, self.selector_post_url)
            hash_id = set_hash_id(address, short_description, parameters)

            if save_new_post_to_db(hash_id, price_byn, price_usd, parameters, address, short_description, post_url, self.city):
                images = get_images_from_post(post)
                if images:
                    for src in images:
                        save_new_image_to_db(src, hash_id)

                # send notification to telegram here

    async def start_parse(self):
        start_page_link = self.get_starting_url()
        page_now = start_page_link

        async with aiohttp.ClientSession() as session:
            while page_now:
                html = await fetch(session, page_now)
                bs = BeautifulSoup(html, 'lxml')
                try:
                    await self.get_all_posts_from_page(bs)
                    next_page = bs.select_one('a[data-testid="realty-pagination-next-link"]')['href']
                    next_page = os.getenv('BASE_URL') + next_page
                    page_now = next_page

                    await random_delay()
                except (TypeError, KeyError):
                    page_now = ''


async def fetch(session, url):
    async with session.get(url, headers=my_headers, timeout=30) as response:
        return await response.text()


def set_clean_byn_price(price):
    if price:
        price = price.replace(' ', '')
        clean_price = price.split('р')[0]
        if is_float(clean_price):
            return float(clean_price)


def set_hash_id(address, short_description, parameters):
    address = address if address else 'Без адреса'
    short_description = short_description if short_description else 'Без описания'
    parameters = parameters if parameters else 'Без параметров'
    if address and short_description:
        return hashlib.sha256(str(short_description + address + parameters).encode()).hexdigest()


def set_clean_usd_price(price):
    if price:
        price = price.replace(' ', '')
        clean_price = price.split('$')[0]
        if is_float(clean_price):
            return float(clean_price)


def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def safe_text_from_post(tag, selector):
    item = tag.select_one(selector)
    if item:
        return item.getText(strip=True)
    else:
        return '-'


def safe_url_from_post(tag, selector):
    url = tag.select_one(selector)
    if url:
        return url['href']
    else:
        return '-'


def get_id_from_url(url):
    if url:
        url_id = (url.split('?')[0]).split('/')[-1]
        return url_id


def get_images_from_post(post):
    html = post.select('div[data-testid^="segment-"]')
    all_urls = []
    if html:
        for i in html:
            src = i['data-testid'].replace('segment-', '')
            all_urls.append(src)
    return all_urls


async def start_parse(min_interval):
    while True:
        vitebsk_parser = Parser('vitebsk')
        mogilev_parser = Parser('mogilev')
        gomel_parser = Parser('gomel')
        brest_parser = Parser('brest')
        minsk_parser = Parser('minsk')
        grodno_parser = Parser('grodno')

        all_parsers = [vitebsk_parser, minsk_parser, mogilev_parser, gomel_parser, brest_parser, grodno_parser]

        for parser in all_parsers:
            await parser.start_parse()
            await random_delay()

        await asyncio.sleep(60 * min_interval)


async def random_delay():
    delay = random.uniform(1.5, 5.6)
    await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(start_parse(5))
