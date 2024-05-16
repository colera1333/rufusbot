import discord
from discord.ext import commands
import anthropic
import os
from youtubesearchpython import VideosSearch
import yt_dlp as youtube_dl
from discord.utils import get
from discord import FFmpegPCMAudio
import asyncio
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

# Set up the Discord bot client
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load your Discord bot token securely
TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize the Claude client
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=anthropic_api_key)

# Spotify API credentials
spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

# Initialize Spotify API client
spotify_credentials = SpotifyClientCredentials(
    client_id=spotify_client_id,
    client_secret=spotify_client_secret
)
spotify_api = Spotify(client_credentials_manager=spotify_credentials)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You need to be in a voice channel for me to join.")

@bot.command(name='play')
async def play(ctx, *, query):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        return await ctx.send("You need to be in a voice channel to play music!")

    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if not voice_client:
        voice_client = await voice_channel.connect()

    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'quiet': True,
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    try:
        url = query
        if not youtube_dl.utils.url_or_none(query):
            videos_search = VideosSearch(query, limit=1)
            result = videos_search.result()
            url = result['result'][0]['link'] if result['result'] else None
            if url:
                print(f"Found YouTube URL: {url}")
            else:
                print("No results found on YouTube.")

        if url:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = next((f['url'] for f in info['formats'] if f['ext'] == 'm4a' or f['ext'] == 'webm'), None)
                if not audio_url:
                    audio_url = info['formats'][0]['url']
                print(f"Streaming URL: {audio_url}")
                player = FFmpegPCMAudio(audio_url, **{
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                })
                voice_client.play(player, after=lambda e: print(f"Finished playing: {e}"))
                await ctx.send(f"Now playing: {query}")
        else:
            await ctx.send("No results found on YouTube.")
    except Exception as e:
        print(f"An error occurred: {e}")
        await ctx.send(f"An error occurred: {e}")
        if voice_client.is_connected():
            await voice_client.disconnect()

@bot.command(name='leave')
async def leave(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("I'm not in a voice channel.")

async def play_spotify_playlist(ctx, playlist_url):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        return await ctx.send("You need to be in a voice channel to play music!")

    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if not voice_client:
        voice_client = await voice_channel.connect()

    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'quiet': True,
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    try:
        playlist_id = playlist_url.split('/').pop().split('?')[0]
        data = spotify_api.playlist_tracks(playlist_id)
        tracks = data['items']

        for track in tracks:
            query = f"{track['track']['name']} {track['track']['artists'][0]['name']}"
            videos_search = VideosSearch(query, limit=1)
            result = videos_search.result()
            url = result['result'][0]['link'] if result['result'] else None

            if url:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    audio_url = next((f['url'] for f in info['formats'] if f['ext'] == 'm4a' or f['ext'] == 'webm'), None)
                    if not audio_url:
                        audio_url = info['formats'][0]['url']
                    player = FFmpegPCMAudio(audio_url, **{
                        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                        'options': '-vn'
                    })
                    voice_client.play(player, after=lambda e: print(f"Finished playing: {e}"))
                    await ctx.send(f"Now playing: {track['track']['name']} by {track['track']['artists'][0]['name']}")
                    
                    # Wait for the current song to finish before playing the next one
                    while voice_client.is_playing():
                        await asyncio.sleep(1)
            else:
                await ctx.send(f"No results found for {track['track']['name']} by {track['track']['artists'][0]['name']}")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        if voice_client.is_connected():
            await voice_client.disconnect()

@bot.command(name='playlist')
async def playlist(ctx, *, playlist_url):
    await play_spotify_playlist(ctx, playlist_url)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Handle LLM responses
    if not message.content.startswith(bot.command_prefix):
        prompt = message.content
        try:
            response_data = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                temperature=0.0,
                system="You are a personal assistant named Rufus.",
                messages=[{"role": "user", "content": prompt}]
            )
            if response_data.content and isinstance(response_data.content, list):
                response = ' '.join(text_block.text for text_block in response_data.content if hasattr(text_block, 'text'))
            else:
                response = 'No response received.'
            await message.channel.send(response)
        except Exception as e:
            print(f"Failed to get response: {e}")
            await message.channel.send("I encountered an error processing your request.")
            return

    await bot.process_commands(message)

# Start the bot
bot.run(TOKEN)
