import os
import asyncio
from telegram import Bot
from selenium import webdriver
from bs4 import BeautifulSoup
import time
from selenium.webdriver.chrome.service import Service

async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")
    bot = Bot(token=bot_token)

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

            name_desc_tag = row.find('td').find_next_sibling('td')
            name_desc = name_desc_tag.text.strip() if name_desc_tag else 'NA'

            location_tag = name_desc_tag.find_next_sibling('td')
            location = location_tag.text.strip() if location_tag else 'NA'

            picture_tag = row.find('td', nowrap='nowrap').find('a')
            picture_url = picture_tag['href'] if picture_tag else 'NA'
            picture_full_url = f"https://www.passiton.org.sg{picture_url}" if picture_url != 'NA' else 'NA'
            validity_td = row.find_all('td')[4]
            validity_text = validity_td.get_text(separator="\n", strip=True)
            caption = f"*New item!*\n" \
                      f"*ID:* {id}\n" \
                      f"*Name Description:*\n {name_desc}\n" \
                      f"*LOCATION COLLECTION/DELIVERY:*\n{location}\n" \
                      f"*VALIDITY ITEM AGE DIMENSION:*\n {validity_text}"
            img_src = row.find('td', nowrap='nowrap').find('img')['src']
            print(picture_full_url)
            img_base_url = 'https://www.passiton.org.sg'
            full_img_url = img_base_url + img_src
            try:
                await bot.send_photo(chat_id=channel_id, photo=full_img_url, caption=caption, parse_mode="Markdown")
            except Exception as e:
                print(f"Error sending photo: {e}")
                await bot.send_message(chat_id=channel_id, text=caption)

    driver.quit()

asyncio.run(main())
