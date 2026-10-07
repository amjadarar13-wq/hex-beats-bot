import os
import asyncio
from threading import Thread
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import os
from threading import Thread
from flask import Flask

# خادم ويب بسيط لربط المنفذ ومنع Render من إيقاف الخدمة
app = Flask('')


@app.route('/')
def home():
  return 'Bot is alive!'


def run():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.start()


# تشغيل خادم الويب
keep_alive()

# ==========================================
# 2. إعدادات البوت والـ Intents
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ تم تسجيل الدخول بنجاح باسم: {bot.user}")

# ==========================================
# 3. إعدادات الصوت والـ YouTube (yt-dlp)
# ==========================================
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'mweb']
        }
    }
}


FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ==========================================
# 4. أوامر الـ Slash Commands
# ==========================================

@bot.tree.command(name="play", description="تشغيل أغنية أو البحث عنها في يوتيوب")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ يجب أن تكون داخل روم صوتي لتشغيل الأغاني!")
        return

    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    try:
        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)
    except Exception as e:
        await interaction.followup.send(f"❌ تعذر الاتصال بالروم الصوتي: {e}")
        return

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))

        if 'entries' in data and len(data['entries']) > 0:
            data = data['entries'][0]

        audio_url = data.get('url')
        title = data.get('title', 'مقطع صوتي')

        if not audio_url:
            await interaction.followup.send("❌ لم يتم العثور على نتائج للبحث.")
            return

        if voice_client.is_playing():
            voice_client.stop()

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        voice_client.play(source)

        await interaction.followup.send(f"🎶 جاري تشغيل: **{title}**")

    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء جلب المقطع: {e}")


@bot.tree.command(name="stop", description="إيقاف التشغيل والخروج من الروم الصوتي")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.followup.send("⏹️ تم إيقاف التشغيل والخروج من الروم الصوتي.")
    else:
        await interaction.followup.send("❌ البوت غير متصل بأي روم صوتي حالياً.")

# ==========================================
# 5. تشغيل البوت
# ==========================================
# ===================================================
# 5. تشغيل البوت
# ===================================================
import os

TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    raise ValueError("لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة!")

bot.run(TOKEN)