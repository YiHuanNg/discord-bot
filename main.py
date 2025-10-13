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
    # Check if user is in a voice channel
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You need to be connected to a voice channel to play music.", ephemeral=True)
        return
    
    # Connect to voice channel
    vc = await interaction.user.voice.channel.connect()
    
    # Define after function to disconnect after playing
    def after_playing(error):
        if error:
            print(f"Error playing audio: {error}")
        coro = vc.disconnect()
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Error disconnecting: {e}")

    # Play audio
    await interaction.response.send_message(f"Playing: {url}")
    vc.play(get_audio_source(url), after=after_playing)

    

# Sync commands with Discord (needed once after startup)
@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("Slash commands synced.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(token)
