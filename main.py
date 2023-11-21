import os
import asyncio

import requests
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from telegram import Bot
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from selenium.webdriver.chrome.service import Service
from telegram.error import RetryAfter
import sqlite3

conn = sqlite3.connect('testinggg.db')
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
            name = lines[0]
            desc = lines[1] if len(lines) > 1 else "NA"
            desc = desc[:500] # truncate if too long; 500 is arbitrary

            location_tag = name_desc_tag.find_next_sibling('td')
            location = location_tag.text.strip() if location_tag else 'NA'

            validity_item_age_dimension_td = row.find_all('td')[4]
            validity_item_age_dimension_text =  validity_item_age_dimension_td.get_text(separator="\n", strip=True)
            lines = validity_item_age_dimension_text.split('\n')
            validity_text = lines[0]
            age_text = lines[1] if len(lines) > 1 else "NA"
            dimensions = lines[2] if len(lines) > 2 else "NA"

            caption = f"*NEW ITEM!*\n" \
                      f"*ID:*\n{id.strip()}\n" \
                      f"*NAME:*\n{name.strip()}\n" \
                      f"*DESCRIPTION:*\n{desc.strip()}\n" \
                      f"*LOCATION COLLECTION/DELIVERY:*\n{location.strip()}\n" \
                      f"*VALIDITY:*\n{validity_text.strip()}\n" \
                      f"*AGE:*\n{age_text.strip()}\n" \
                      f"*DIMENSIONS:*\n{dimensions.strip()}\n" \

            img_base_url = 'https://www.passiton.org.sg'
            web_url = img_base_url + f"/view-image?id={id}"
            driver.get(web_url)
            time.sleep(5)
            image_source = driver.page_source
            image_soup = BeautifulSoup(image_source, 'html.parser')
            div_element = image_soup.find("div", style="clear:both; margin-top:30px;")
            if div_element:
                img_tag = div_element.find("img")
                if img_tag:
                    img_src = img_tag.get("src")
                    full_img_url = img_base_url + img_src
                else:
                    write_data_into_file("data.txt",str(image_soup.prettify()))
                    print("Image tag not found.")
                    return
            else:
                print("Div element not found.")
            try:
                print(full_img_url)
                await bot.send_photo(chat_id=channel_id, photo=full_img_url, caption=caption, parse_mode="Markdown")
            except RetryAfter as e:
                print(f"Hit rate limit.. retrying after {e.retry_after}")
                time.sleep(e.retry_after)
            except Exception as e:
                print(f"Error sending photo: {e}")
                # this line may cause duplicate image to be sent
                await bot.send_message(chat_id=channel_id, text=caption,parse_mode="Markdown")

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