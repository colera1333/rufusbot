import discord
from discord.ext import commands
import anthropic
import os

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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # General response handler, works in both guilds and private messages
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
        await message.channel.send(response)  # Send response in any context
    except Exception as e:
        print(f"Failed to get response: {e}")
        await message.channel.send("I encountered an error processing your request.")
        return

    # Voice channel specific commands, only in guild context
    if message.guild and "join" in response.lower():
        member = message.guild.get_member(message.author.id) if not isinstance(message.author, discord.Member) else message.author
        if member.voice:
            voice_channel = member.voice.channel
            if voice_channel:
                voice_client = await voice_channel.connect()
                await message.channel.send(f"Joined {voice_channel.name}")
            else:
                await message.channel.send("You need to be in a voice channel for me to join.")
        else:
            await message.channel.send("You are not in a voice channel.")

    # Process other commands if there are any
    await bot.process_commands(message)

# Start the bot
bot.run(TOKEN)
