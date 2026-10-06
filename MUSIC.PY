import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from collections import defaultdict
from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "HEX Beats Bot is Running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# تشغيل خادم الويب في مسار خلفي منفصل
Thread(target=run_web).start()
# --- إعدادات البوت والـ Intents ---
intents = discord.Intents.default()
intents.message_content = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.queues = defaultdict(list)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ تم تسجيل أوامر الـ Slash Commands بنجاح!")

bot = MusicBot()

# --- خيارات محسنة وسريعة جداً لـ yt-dlp و FFmpeg ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'nocheckcertificate': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch1:',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 32k -analyzeduration 0',
    'options': '-vn -bufsize 64k',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

def play_next(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if bot.queues[guild_id]:
        next_song = bot.queues[guild_id].pop(0)
        url = next_song['url']
        title = next_song['title']

        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        interaction.guild.voice_client.play(
            source, 
            after=lambda e: play_next(interaction)
        )
        asyncio.run_coroutine_threadsafe(
            interaction.channel.send(f"🎶 **جاري التشغيل الآن:** `{title}`"), 
            bot.loop
        )

@bot.event
async def on_ready():
    print(f'🤖 تم تشغيل البوت باسم: {bot.user.name}')

# --- الأوامر ---

@bot.tree.command(name="join", description="Joins your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ يجب أن تكون متصلاً بقناة صوتية أولاً!", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    if interaction.guild.voice_client is None:
        await channel.connect()
        await interaction.response.send_message(f"🔊 تم الانضمام إلى: **{channel.name}**")
    else:
        await interaction.guild.voice_client.move_to(channel)
        await interaction.response.send_message(f"🔄 تم الانتقال إلى: **{channel.name}**")

@bot.tree.command(name="play", description="Play a song")
@app_commands.describe(search="اسم الأغنية أو الرابط من يوتيوب")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send("❌ يجب أن تكون متصلاً بقناة صوتية لاستخدام هذا الأمر!")
        return

    voice_client = interaction.guild.voice_client
    if voice_client is None:
        voice_client = await interaction.user.voice.channel.connect()

    # جلب معلومات المقطع في الخفاء لتفادي التجميد والبطء
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(
            None, 
            lambda: ytdl.extract_info(f"ytsearch:{search}", download=False)
        )
    except Exception as e:
        await interaction.followup.send("❌ حدث خطأ أثناء جلب الصوت من يوتيوب.")
        return

    # معالجة آمنة للبيانات لتجنب KeyError: 'url'
    if 'entries' in data and len(data['entries']) > 0:
        info = data['entries'][0]
    else:
        info = data

    url = info.get('url') or info.get('webpage_url')
    title = info.get('title', 'صوت غير معروف')

    if not url:
        await interaction.followup.send("❌ لم يتم العثور على رابط صوت صالح.")
        return

    song_data = {'url': url, 'title': title}

    if voice_client.is_playing() or voice_client.is_paused():
        bot.queues[interaction.guild_id].append(song_data)
        await interaction.followup.send(f"➕ **تمت الإضافة إلى قائمة الانتظار:** `{title}`")
    else:
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        voice_client.play(source, after=lambda e: play_next(interaction))
        await interaction.followup.send(f"🎶 **جاري التشغيل الآن:** `{title}`")

@bot.tree.command(name="skip", description="Skips to the next song")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("⏭️ تم تخطي الأغنية الحالية.")
    else:
        await interaction.response.send_message("❌ لا يوجد شيء يعمل حالياً لتخطيه.", ephemeral=True)

@bot.tree.command(name="stop", description="Stops the music and clears the queue")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        bot.queues[interaction.guild_id].clear()
        await voice_client.disconnect()
        await interaction.response.send_message("⏹️ تم إيقاف التشغيل، تفريغ القائمة، والمغادرة.")
    else:
        await interaction.response.send_message("❌ البوت غير متصل بأي قناة صوتية حالياً.", ephemeral=True)
import os

import os

# يقرأ التوكن من متغيرات البيئة (مثل Render)، وإذا لم يجدها يستخدم التوكن المحلي
TOKEN = os.getenv("DISCORD_TOKEN") or "MTU1MDQ1OTMyNjYzODg1NDMwNg.GBeR7T.LtC4yVeEpReR2FecdjyeU0wLWyYcFW4YERz-7E"

bot.run(TOKEN)