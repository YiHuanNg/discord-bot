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
    # Defer response to allow time for processing
    await interaction.response.defer()

    # Check if user is in a voice channel
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("You need to be connected to a voice channel to play music.", ephemeral=True)
        return
    
    # Connect or move to voice channel
    user_channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if vc:
        if vc.channel != user_channel:
            await vc.move_to(user_channel)
    else:
        vc = await user_channel.connect()

    # Stop current audio if playing
    if vc.is_playing():
        vc.stop()
    
    # Get audio source
    source = get_audio_source(url)
    if not source:
        await interaction.followup.send("Could not retrieve audio from the provided URL.", ephemeral=True)
        return

    # Disconnect after idle timeout
    async def disconnect_after_idle(vc, delay=60):
        await asyncio.sleep(delay) 
        if vc.is_connected() and not vc.is_playing():
            await vc.disconnect()
            print("Disconnected due to inactivity.")

    # Disconnect after playing
    def after_playing(error):
        if error:
            print(f"Error playing audio: {error}")
        asyncio.run_coroutine_threadsafe(disconnect_after_idle(vc), bot.loop)

    # Play audio
    await interaction.followup.send(f"Playing: {url}")
    vc.play(source, after=after_playing)

# Stop music
@bot.tree.command(name="stop", description="Stop the music and disconnect")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        vc.stop()
        await vc.disconnect()
        await interaction.response.send_message("Stopped the music and disconnected.")
    else:
        await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)

# Sync commands with Discord (needed once after startup)
@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("Slash commands synced.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(token)
