import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import yt_dlp
import asyncio

# Load token
load_dotenv()
token = os.getenv("DISCORD_BOT_TOKEN")

# Logging
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Use commands.Bot for slash commands
bot = commands.Bot(command_prefix="!", intents=intents)

def get_audio_source(url):
    info = yt_dlp.YoutubeDL({'format': 'bestaudio', 'noplaylist': 'True'}).extract_info(url, download=False)
    audio_url = info['url']
    return discord.FFmpegPCMAudio(audio_url)



# Slash command test
@bot.tree.command(name="hello", description="Say hello to the bot")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")

# Ping command
@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")

# Play music
@bot.tree.command(name="play", description="Play a song from YouTube")
async def play(interaction: discord.Interaction, url: str):
    vc = await interaction.user.voice.channel.connect()
    
    await interaction.response.send_message(f"Playing: {url}")
    source = get_audio_source(url)
    vc.play(source)

    

# Sync commands with Discord (needed once after startup)
@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("Slash commands synced.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(token)
