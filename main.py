import os
import asyncio

from PIL import Image
from io import BytesIO
import requests
from telegram import Bot
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from selenium.webdriver.chrome.service import Service
from telegram.error import RetryAfter
import sqlite3

conn = sqlite3.connect('testingg13.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY)''')
conn.commit()

def is_item_sent(item_id):
    cursor.execute("SELECT id FROM items WHERE id = ?", (item_id,))
    return cursor.fetchone() is not None

def mark_item_as_sent(item_id):
    cursor.execute("INSERT INTO items (id) VALUES (?)", (item_id,))
    conn.commit()

def write_data_into_file(file_name,content):
    try:
        with open(file_name, 'w') as file:
            file.write(content)
    except IOError as e:
        print(f"Error while writing to file: {e}")

def download_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception("Failed to download image")

def compress_image(image_bytes, quality=85):
    img = Image.open(image_bytes)
    img_io = BytesIO()
    img.save(img_io, 'JPEG', quality=quality)
    img_io.seek(0)
    return img_io

async def send_photo(bot, chat_id, photo_url, caption):
    try:
        await bot.send_photo(chat_id=chat_id, photo=photo_url, caption=caption, parse_mode="Markdown")
        return True
    except RetryAfter as e:
        print(f"Hit rate limit, retrying after {e.retry_after} seconds.")
        time.sleep(e.retry_after)
        send_photo(bot,chat_id,photo_url,caption)
    except Exception as e:
        print(f"Exception occured while sending photo: {e}")
        print(f"Exception occured while sending photo url: {photo_url}")
        for quality in range(80, 0, -5):
          image_bytes = download_image(photo_url)
          compressed_photo = compress_image(image_bytes,quality)
          try:
            is_photo_sent = await send_photo(bot,chat_id,compressed_photo,caption)
            if is_photo_sent:
              return True
          except Exception as e:
              print(f"Exception occured while sending photo: {e}")
              continue
    return False

async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    bot = Bot(token=bot_token)
    current_page_number = 1

    s = Service('/Users/kevinloh/Downloads/chromedriver-mac-arm64/chromedriver')
    driver = webdriver.Chrome(service=s)
    url = 'https://www.passiton.org.sg/item-list'
    driver.get(url)

    while True:
        row_number = 0
        print(f"We are at page number {current_page_number}")
        time.sleep(5)
        source = driver.page_source
        soup = BeautifulSoup(source, 'html.parser')
        write_data_into_file("passiton.html", str(soup.prettify()))
        write_data_into_file("line-even.html", str(soup.find_all('tr', class_='lineEven')))
        write_data_into_file("line-odd.html", str(soup.find_all('tr', class_='lineOdd')))
        rows = soup.find_all('tr', class_='lineEven') + soup.find_all('tr', class_='lineOdd')
        if len(rows) == 0:
            break
        for row in rows:
            row_number = row_number + 1
            id_cell = row.find('td', style='width:20px;')
            id = id_cell.text.strip() if id_cell else 'NA'

            if is_item_sent(id):
                continue
            else:
                mark_item_as_sent(id)

            name_desc_tag = id_cell.find_next_sibling('td')
            name_desc = name_desc_tag.text.strip() if name_desc_tag else 'NA'
            lines = name_desc.split('\n')
            name = lines[0].strip()
            desc = lines[1].strip() if len(lines) > 1 else "NA"
            desc = desc[:500] # truncate if too long; 500 is arbitrary

            location_tag = name_desc_tag.find_next_sibling('td')
            location = location_tag.text.strip() if location_tag else 'NA'
            location = '-' if len(location) == 0 else location

            validity_item_age_dimension_td = location_tag.find_next_sibling('td').find_next_sibling('td')
            validity_item_age_dimension_text = validity_item_age_dimension_td.get_text(separator="\n", strip=True)
            lines = validity_item_age_dimension_text.split('\n')
            validity_text = lines[0].strip()
            age_text = lines[1].strip() if len(lines) > 1 else "NA"
            dimensions = lines[2].strip() if len(lines) > 2 else "NA"
            # https://www.passiton.org.sg/item-list?search=1&search_by=id&search_id=128196&ItemCat1=&ItemSubCat1=

            item_url = f"https://www.passiton.org.sg/item-list?search=1&search_by=id&search_id={id}&ItemCat1=&ItemSubCat1="
            caption = (f"*NEW ITEM* [🔗]({item_url})\n"
                       f"*ID:*\n{id}\n"
                       f"*NAME:*\n{name}\n"
                       f"*DESCRIPTION:*\n{desc}\n"
                       f"*LOCATION COLLECTION/DELIVERY:*\n{location}\n"
                       f"*VALIDITY:*\n{validity_text}\n"
                       f"*AGE:*\n{age_text}\n"
                       f"*DIMENSIONS:*\n{dimensions}\n")

            caption = caption[:1024] # telegram max characters in a message limit
            img_base_url = 'https://www.passiton.org.sg'
            web_url = img_base_url + f"/view-image?id={id}"
            driver.get(web_url)
            time.sleep(5)
            image_source = driver.page_source
            image_soup = BeautifulSoup(image_source, 'html.parser')
            div_element = image_soup.find("div", style="clear:both; margin-top:30px;")
            if div_element:
                img = div_element.find("img")
                if img:
                    img_src = img.get("src")
                    full_img_url = img_base_url + img_src
                else:
                    print("Image not found.")
                    return
            else:
                print("Div element not found.")
            is_photo_sent = await send_photo(bot, channel_id, full_img_url, caption)
            if is_photo_sent:
                print(f"image with id {id} sent successfully")
                print(f"image with url {full_img_url} sent successfully")
            else:
                print("it should never reach here")
                print(f"image with id {id} not sent successfully")
                print(f"image not sent {full_img_url}")
                # i couldnt get it to work with mark down
                caption = (f"<b>NEW ITEM:</b> <a href='{item_url}'>🔗</a>\n"
                           f"<b>ID:</b> {id}\n"
                           f"<b>NAME:</b> {name}\n"
                           f"<b>DESCRIPTION:</b> {desc}\n"
                           f"<b>LOCATION COLLECTION/DELIVERY:</b> {location}\n"
                           f"<b>VALIDITY:</b> {validity_text}\n"
                           f"<b>AGE:</b> {age_text}\n"
                           f"<b>DIMENSIONS:</b> {dimensions}\n"
                           f"<b>PHOTO URL:</b> <a href='{full_img_url}'>View Photo</a>\n")

                caption = caption[:1024]
                await bot.send_message(chat_id=channel_id, text=caption, parse_mode="HTML")
        current_page_number = current_page_number + 1
        url = f'https://www.passiton.org.sg/item-list&pg={current_page_number}'
        driver.get(url)

    driver.quit()

asyncio.run(main())

