import os
import asyncio
import traceback
from datetime import datetime
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
DATABASE_ID = os.getenv("DATABASE_ID")
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

old_pages = None


async def get_notion_pages() -> List[dict]:
    """
    Fetch pages from the Notion database since the last checked timestamp.

    :return: A list of pages.
    """
    global last_checked
    try:
        pages = notion.databases.query(**{"database_id": DATABASE_ID}).get("results")
        last_checked = datetime.utcnow().replace(microsecond=0).isoformat()
        logger.info(f"Last checked at: {last_checked}")
        logger.debug(pages)
        return pages
    except Exception as e:
        logger.error(f"Error fetching pages from Notion: {e}")
        return []


def find_card(database: list[dict], id_card: str):
    for page1 in database:
        if id_card == page1["id"]:
            return page1
    return None


async def embed_new_card(card: dict):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        await channel.send(embed=discord.Embed(title="Создана новая карточка",
                                               description="`" + name_card(card) + "`",
                                               color=65535
                                               ))
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_change_card(card_name: str, old_value, new_value):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        await channel.send(embed=discord.Embed(title="Изменился статус: " + card_name,
                                               description="Был: " + "`" + old_value + "`\n" + "Cтал: " + "`" + new_value + "`",
                                               color=65535
                                               ))
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_addperson(card_name: str, person_name: str):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        await channel.send(embed=discord.Embed(title="Добавлен пользователь",
                                               description="Карточка: " + "`" + card_name + "`" + "\n" + "Пользователь: " + "`" + person_name + "`",
                                               color=65535
                                               ))
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_delete_person(card_name: str, person_name: str):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        await channel.send(embed=discord.Embed(title="Удален пользователь",
                                               description="Карточка: " + "`" + card_name + "`" + "\n" + "Пользователь: " + "`" + person_name + "`",
                                               color=65535
                                               ))
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


async def embed_delete_card(card: dict):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    try:
        await channel.send(embed=discord.Embed(title="Удалена карточка",
                                               description="`" + name_card(card) + "`",
                                               color=65535
                                               ))
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")


def name_card(card: dict):
    title = card["properties"]["Name"]["title"]
    if len(title) == 0:
        return "Untitled"
    return title[0]["text"]["content"]


async def poll_notion_database() -> None:
    """
    Poll the Notion database and send updates to a Discord channel.
    """
    global old_pages
    while True:
        new_pages = await get_notion_pages()
        if old_pages is None:
            old_pages = new_pages
            continue

        for card in new_pages:
            old_card = find_card(old_pages, card["id"])
            if old_card is None:
                await embed_new_card(card)
                continue

            elif card["properties"]["Lifecycle"] != old_card["properties"]["Lifecycle"]:
                await embed_change_card(name_card(card), old_card["properties"]["Lifecycle"]["select"]["name"], card["properties"]["Lifecycle"]["select"]["name"])

            elif card["properties"]["Assign"]["people"] != old_card["properties"]["Assign"]["people"]:
                old_people = old_card["properties"]["Assign"]["people"]
                new_people = card["properties"]["Assign"]["people"]

                for person in new_people:
                    if person in old_people:
                        continue
                    await embed_addperson(name_card(card), person["name"])

                for person in old_people:
                    if person in new_people:
                        continue
                    await embed_delete_person(name_card(card), person["name"])

        for card in old_pages:
            new_card = find_card(new_pages, card["id"])
            if new_card is None:
                await embed_delete_card(card)

        old_pages = new_pages
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
