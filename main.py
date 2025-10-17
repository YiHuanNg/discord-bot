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

# Music queue
queues = {}

# Function to get audio source from YouTube URL
def get_audio_source(url):
    info = yt_dlp.YoutubeDL({'format': 'bestaudio', 'noplaylist': 'True'}).extract_info(url, download=False)
    audio_url = info['url']
    title = info.get('title', url)
    return discord.FFmpegPCMAudio(audio_url), title

# Function to play next in queue
async def play_next(interaction, vc):
    guild_id = interaction.guild.id

    # If queue is empty, disconnect after timeout
    if guild_id not in queues or not queues[guild_id]:
        async def disconnect_after_idle(vc, delay=60):
            await asyncio.sleep(delay) 
            if vc.is_connected() and not vc.is_playing():
                await vc.disconnect()
                print("Disconnected due to inactivity.")
        asyncio.create_task(disconnect_after_idle(vc))
        return

    # Play next in queue
    url, title, source = queues[guild_id].pop(0)
    vc.current_title = title  # Store title for now playing

    # Announce now playing
    channel = interaction.channel or (vc.channel if vc and vc.channel else None)
    if channel:
        await channel.send(f"Now playing: {url}")
    
    def after_playing(error):
        if error:
            print(f"Error playing next: {error}")
        asyncio.run_coroutine_threadsafe(play_next(interaction, vc), bot.loop)

    vc.play(source, after=after_playing)

# SLASH COMMANDS
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
    
    # Get audio source
    source, title = get_audio_source(url)
    if not source:
        await interaction.followup.send("Could not retrieve audio from the provided URL.", ephemeral=True)
        return

    # Initialize queue for guild if not exists
    guild_id = interaction.guild.id
    if guild_id not in queues:
        queues[guild_id] = []

    # If already playing, add to queue
    if vc.is_playing():
        queues[guild_id].append((url, title, source))
        await interaction.followup.send(f"Added to queue: {url}")
    else:
        # Else, play immediately
        await interaction.followup.send(f"Playing: {url}")

        def after_playing(error):
            if error:
                print(f"Error playing audio: {error}")
            asyncio.run_coroutine_threadsafe(play_next(interaction, vc), bot.loop)

        vc.play(source, after=after_playing)
        vc.current_title = title  # Store title for now playing

# Stop music
@bot.tree.command(name="stop", description="Stop the music and disconnect")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    guild_id = interaction.guild.id

    # Stop and clear queue if connected
    if vc and vc.is_connected():
        vc.stop()

        if guild_id in queues:
            queues[guild_id].clear()

        await vc.disconnect()
        await interaction.response.send_message("Stopped the music and disconnected.")
    else:
        # Not connected
        await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)

# Show queue
@bot.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = interaction.guild.voice_client

    # Build now playing message
    current_song_msg = ""
    if vc and hasattr(vc, 'current_title'):
        current_song_msg = f"Now Playing: {vc.current_title}\n"

    # Build queue message
    queue_msg = ""
    if guild_id in queues and len(queues[guild_id]) > 0:
        queue_list = "\n".join([f"{idx + 1}. {item[1]}" for idx, item in enumerate(queues[guild_id])])
        queue_msg = f"Up Next:\n{queue_list}"

    # If nothing is playing and queue is empty
    if not current_song_msg and not queue_msg:
        await interaction.response.send_message("Nothing is playing, and the queue is empty.", ephemeral=True)
        return

    await interaction.response.send_message(current_song_msg + queue_msg)

# Skip current song
@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client

    # Check if connected and playing
    if vc and vc.is_connected():
        if vc.is_playing():
            vc.stop()
            await interaction.response.send_message("Skipped the current song.")
        else:
            await interaction.response.send_message("No song is currently playing.", ephemeral=True)
    else:
        await interaction.response.send_message("I am not connected to a voice channel.", ephemeral=True)


# Sync commands with Discord (needed once after startup)
@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("Slash commands synced.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(token)
