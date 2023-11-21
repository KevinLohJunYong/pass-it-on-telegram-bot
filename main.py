import os
import asyncio

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from telegram import Bot
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from selenium.webdriver.chrome.service import Service
from telegram.error import RetryAfter
import sqlite3

conn = sqlite3.connect('testingg3.db')
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

async def send_photo(bot, chat_id, photo_url, caption):
    try:
        await bot.send_photo(chat_id=chat_id, photo=photo_url, caption=caption, parse_mode="Markdown")
        return True
    except RetryAfter as e:
        print(f"Hit rate limit, retrying after {e.retry_after} seconds.")
        time.sleep(e.retry_after)
    except Exception as e:
        print(f"Exception occured while sending photo: {e}")
        time.sleep(5)
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
        time.sleep(5)
        source = driver.page_source
        soup = BeautifulSoup(source, 'html.parser')

        rows = soup.find_all('tr', class_='lineEven') + soup.find_all('tr', class_='lineOdd')
        for row in rows:

            id_cell = row.find('td', style='width:20px;')
            id = id_cell.text.strip() if id_cell else 'NA'

            if is_item_sent(id):
                continue
            else:
                mark_item_as_sent(id)

            name_desc_tag = row.find('td').find_next_sibling('td')
            name_desc = name_desc_tag.text.strip() if name_desc_tag else 'NA'
            lines = name_desc.split('\n')
            name = lines[0].strip()
            desc = lines[1].strip() if len(lines) > 1 else "NA"
            desc = desc[:500] # truncate if too long; 500 is arbitrary

            location_tag = name_desc_tag.find_next_sibling('td')
            location = location_tag.text.strip() if location_tag else 'NA'

            validity_item_age_dimension_td = row.find_all('td')[4]
            validity_item_age_dimension_text = validity_item_age_dimension_td.get_text(separator="\n", strip=True)
            lines = validity_item_age_dimension_text.split('\n')
            validity_text = lines[0].strip()
            age_text = lines[1].strip() if len(lines) > 1 else "NA"
            dimensions = lines[2].strip() if len(lines) > 2 else "NA"

            caption = f"*NEW ITEM!*\n" \
                      f"*ID:*\n{id}\n" \
                      f"*NAME:*\n{name}\n" \
                      f"*DESCRIPTION:*\n{desc}\n" \
                      f"*LOCATION COLLECTION/DELIVERY:*\n{location}\n" \
                      f"*VALIDITY:*\n{validity_text}\n" \
                      f"*AGE:*\n{age_text}\n" \
                      f"*DIMENSIONS:*\n{dimensions}\n"

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
                    print(f"full img url: {full_img_url}")
                else:
                    write_data_into_file("data2.txt",img)
                    print("Image not found.")
                    return
            else:
                print("Div element not found.")
            is_photo_sent = await send_photo(bot, channel_id, full_img_url, caption)
            if not is_photo_sent:
                print(f"image not sent {full_img_url}")
                # i couldnt get it to work with mark down
                caption = (f"<b>NEW ITEM!</b>\n"
                           f"<b>ID:</b>\n{id}\n"
                           f"<b>NAME:</b>\n{name}\n"
                           f"<b>DESCRIPTION:</b>\n{desc}\n"
                           f"<b>LOCATION COLLECTION/DELIVERY:</b>\n{location}\n"
                           f"<b>VALIDITY:</b>\n{validity_text}\n"
                           f"<b>AGE:</b>\n{age_text}\n"
                           f"<b>DIMENSIONS:</b>\n{dimensions}\n"
                           f"<b>PHOTO URL:</b>\n<a href='{full_img_url}'>{full_img_url}</a>\n")
                print(caption)
                caption = caption[:1024]
                await bot.send_message(chat_id=channel_id, text=caption, parse_mode="HTML")
        try:
            page_links = driver.find_elements(By.CSS_SELECTOR, "div[style='float:right;'] a")
            expected_next_page_number = current_page_number + 1
            for link in page_links:
                candidate_next_page_number = link.text.strip()
                if  candidate_next_page_number == str(expected_next_page_number):
                    link.click()
                    print("went to next page successfully")
                    break
        except NoSuchElementException:
            print("Page link not found")
        current_page_number += 1

    driver.quit()

asyncio.run(main())

