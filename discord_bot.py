import json
import os
import asyncio
import traceback
from datetime import datetime, timedelta
import logging
from typing import List

import discord
from discord import Intents
from discord.ext import commands
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve values from environment variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASES_ID = json.loads(os.environ["DATABASE_ID"])
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 120))
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()

# Configure logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
)
logger = logging.getLogger(__name__)
logger.setLevel(LOGLEVEL)
logger.addHandler(console_handler)

# Create default intents and disable members intent
intents = Intents.default()

# Initialize the Discord bot with the specified intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize the Notion client
notion = Client(auth=NOTION_API_KEY)

# Store the last checked timestamp
last_checked = datetime.utcnow().replace(microsecond=0).isoformat()

#
time_msg = (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%y  %H:%M')

old_databases = None


class Databases:
    def __init__(self, name, pages):
        self.name = name
        self.pages = pages


async def get_notion_pages(database_id: str) -> List[dict]:
    """
    Fetch pages from the Notion database since the last checked timestamp.

    :return: A list of pages.
    """
    global last_checked
    try:
        pages = notion.databases.query(**{"database_id": database_id}).get("results")
        last_checked = datetime.utcnow().replace(microsecond=0).isoformat()
        logger.info(f"Last checked at: {last_checked}")
        logger.debug(pages)
        await asyncio.sleep(1)
        return pages
    except Exception as e:
        logger.error(f"Error fetching pages from Notion: {e}")
        return []


def find_card(database: list[dict], id_card: str):
    for page1 in database:
        if id_card == page1["id"]:
            return page1
    return None


def find_persons(people):
    persons = "не выбрано"
    for person in people:
        if persons == "не выбрано":
            persons = ""
            persons += str(person["name"])
        else:
            persons += ", " + str(person["name"])
    return persons


async def embed_new_card(card: dict, name_database):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        status = "Не найден"
        if find_status(card["properties"]) is not None:
            status = find_status(card["properties"])

        embed = discord.Embed(title=name_card(card),
                              color=int("02b564", 16))

        embed.set_author(name="Создана новая карточка", icon_url="https://i.imgur.com/Y8YJYEK.png")
        embed.add_field(name="Пользователь(-ли):", value=find_persons(card["properties"]["Assign"]["people"]), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Статус выполнения:", value=status, inline=True)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text=name_database + "  |  " + time_msg)

        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_change_card(card_name: str, old_value, new_value, name_database):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        embed = discord.Embed(title=card_name,
                              color=int("eb6d22", 16))

        embed.set_author(name="Изменился статус", icon_url="https://i.imgur.com/fEqqtzf.png")
        embed.add_field(name="Прошлый статус:", value=old_value, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Новый статус:", value=new_value, inline=True)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text=name_database + "  |  " + time_msg)

        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_add_person(card_name: str, person_name: str, name_database, card):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        embed = discord.Embed(title=card_name,
                              color=int("02b564", 16))

        embed.set_author(name="Добавлен пользователь", icon_url="https://i.imgur.com/LeQOd0N.png")
        embed.add_field(name="Новый пользователь: ", value=person_name, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Все пользователи: ", value=find_persons(card["properties"]["Assign"]["people"]), inline=True)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text=name_database + "  |  " + time_msg)

        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_delete_person(card_name: str, person_name: str, name_database, card):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        embed = discord.Embed(title=card_name,
                              color=int("aa2012", 16))

        embed.set_author(name="Удален пользователь", icon_url="https://i.imgur.com/8HeH8Py.png")
        embed.add_field(name="Удаленный пользователь: ", value=person_name, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Все пользователи: ", value=find_persons(card["properties"]["Assign"]["people"]), inline=True)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text=name_database + "  |  " + time_msg)

        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_delete_card(card: dict, name_database, old_card):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        status = "Не найден"
        if find_status(old_card["properties"]) is not None:
            status = find_status(card["properties"])

        embed = discord.Embed(title=name_card(card),
                              color=int("aa2012", 16))

        embed.set_author(name="Удалена карточка", icon_url="https://i.imgur.com/mUqxBYO.png")
        embed.add_field(name="Пользователь(-ли):", value=find_persons(card["properties"]["Assign"]["people"]), inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Статус выполнения:", value=status, inline=True)
        embed.add_field(name=" ", value=" ", inline=False)
        embed.set_footer(text=name_database + "  |  " + time_msg)

        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


def name_card(card: dict):
    title = card["properties"]["Name"]["title"]
    if len(title) == 0:
        return "Untitled"
    return title[0]["text"]["content"]


def find_old_page(name):
    global old_databases
    for element in old_databases:
        if element.name == name:
            return element.pages
    return None


def find_status(properties: dict):
    for key in properties.keys():
        if key == "Lifecycle":
            if properties["Lifecycle"]["select"] is not None:
                return properties["Lifecycle"]["select"]["name"]
            else:
                return None
        elif key == "Status":
            return properties["Status"]["status"]["name"]
    return None


async def poll_notion_database() -> None:
    """
    Poll the Notion database and send updates to a Discord channel.
    """
    global old_databases
    while True:
        new_databases = []
        databases_keys = DATABASES_ID.keys()
        for database_name in databases_keys:
            page = await get_notion_pages(DATABASES_ID[database_name])
            new_databases.append(Databases(database_name, page))

        if old_databases is None:
            old_databases = new_databases
            continue

        for database in new_databases:
            new_pages = database.pages
            old_pages = find_old_page(database.name)

            for card in new_pages:
                old_card = find_card(old_pages, card["id"])
                if old_card is None:
                    await embed_new_card(card, database.name)
                    continue

                elif find_status(card["properties"]) != find_status(old_card["properties"]) and find_status(card["properties"]) is not None:
                    await embed_change_card(name_card(card), find_status(old_card["properties"]),
                                            find_status(card["properties"]), database.name)

                elif card["properties"]["Assign"]["people"] != old_card["properties"]["Assign"]["people"]:
                    old_people = old_card["properties"]["Assign"]["people"]
                    new_people = card["properties"]["Assign"]["people"]

                    for person in new_people:
                        if person in old_people:
                            continue
                        await embed_add_person(name_card(card), person["name"], database.name, card)

                    for person in old_people:
                        if person in new_people:
                            continue
                        await embed_delete_person(name_card(card), person["name"], database.name, card)

            for card in old_pages:
                new_card = find_card(new_pages, card["id"])
                if new_card is None:
                    await embed_delete_card(card, database.name, find_card(old_pages, card["id"]))

        old_databases = new_databases
        await asyncio.sleep(POLL_INTERVAL)  # Poll every N seconds


@bot.event
async def on_ready() -> None:
    """
    Event that occurs when the bot is ready.
    """
    logger.info(f"{bot.user} is now online!")
    try:
        await poll_notion_database()
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error polling Notion database: {e}")


if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
