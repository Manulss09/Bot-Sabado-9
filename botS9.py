import discord
from discord.ext import commands
import random
import yt_dlp as youtube_dl
import asyncio
import secrets
import string
import os
import requests

# --- Configuración de intents ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("/"), description="Bot combinado", intents=intents)

# --- YouTube DL configuración ---
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ffmpeg_options = {
    'options': '-vn',
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# --- Clases de Música ---
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"🔊 Movido al canal de voz: {channel.name}")
        else:
            await channel.connect()
            await ctx.send(f"✅ Conectado al canal de voz: {channel.name}")

    @commands.command()
    async def play(self, ctx, *, query):
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print(f'❌ Player error: {e}') if e else None)
        await ctx.send(f'🎵 Reproduciendo: {query}')

    @commands.command()
    async def yt(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print(f'❌ Player error: {e}') if e else None)
        await ctx.send(f'🎶 Reproduciendo desde YouTube: **{player.title}**')

    @commands.command()
    async def stream(self, ctx, *, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'❌ Player error: {e}') if e else None)
        await ctx.send(f'📡 Transmitiendo: **{player.title}**')

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client:
            ctx.voice_client.source.volume = volume / 100
            await ctx.send(f'🔊 Volumen ajustado a {volume}%')
        else:
            await ctx.send("⚠️ No estoy conectado a un canal de voz.")

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("🛑 Me desconecté del canal de voz.")
        else:
            await ctx.send("⚠️ No estoy conectado a ningún canal de voz.")

    @play.before_invoke
    @yt.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("⚠️ No estás en un canal de voz.")
                raise commands.CommandError("El autor no está en un canal de voz.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

# --- Funciones adicionales anteriores ---
@bot.command()
async def repetir(ctx, *, texto):
    await ctx.send(texto)

@bot.command()
async def dado(ctx):
    await ctx.send(f'🎲 Has sacado un {random.randint(1,6)}')

@bot.command()
async def generar_password(ctx):
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(chars) for _ in range(12))
    await ctx.send(f'🔐 Contraseña generada: `{password}`')

# --- Comandos matemáticos y de utilidad ---
@bot.command()
async def add(ctx, a: int, b: int):
    await ctx.send(f'🧮 Resultado: {a + b}')

@bot.command()
async def roll(ctx, dice: str):
    try:
        rolls, limit = map(int, dice.lower().split('d'))
        results = [random.randint(1, limit) for _ in range(rolls)]
        await ctx.send(f'🎲 Resultados: {results} (Total: {sum(results)})')
    except:
        await ctx.send('⚠️ Usa el formato NdN, por ejemplo 2d6')

@bot.command()
async def choose(ctx, *choices: str):
    if choices:
        await ctx.send(f'🤔 Yo elijo: {random.choice(choices)}')
    else:
        await ctx.send('⚠️ Proporciona opciones para elegir.')

@bot.command()
async def repeat(ctx, times: int, *, content: str):
    if times > 10:
        await ctx.send("⚠️ Máximo 10 repeticiones.")
    else:
        for _ in range(times):
            await ctx.send(content)

@bot.command()
async def joined(ctx, member: discord.Member):
    await ctx.send(f'📅 {member.name} se unió el {member.joined_at.strftime("%d/%m/%Y")}')

@bot.command(name="cool")
async def cool_bot(ctx, *, text: str):
    if text.lower() == "bot":
        await ctx.send("😎 ¡Gracias! Yo sé que soy cool.")
    else:
        await ctx.send("❓ ¿Seguro que eso es cool?")

@bot.command()
async def password(ctx, length: int):
    if not 0 < length <= 100:
        await ctx.send("⚠️ La longitud debe ser entre 1 y 100 caracteres.")
        return
    chars = string.ascii_letters + string.digits + string.punctuation
    passwd = ''.join(secrets.choice(chars) for _ in range(length))
    await ctx.send(f'🔑 Contraseña: `{passwd}`')

# --- Comandos secretos ---
@bot.group()
async def secret(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("🕵️ Usa un subcomando: text, voice o emoji")

@secret.command()
async def text(ctx, nombre: str, *, usuarios_roles: str):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    for name in usuarios_roles.split():
        role_or_user = discord.utils.get(ctx.guild.roles, name=name) or discord.utils.get(ctx.guild.members, name=name)
        if role_or_user:
            overwrites[role_or_user] = discord.PermissionOverwrite(view_channel=True)
    canal = await ctx.guild.create_text_channel(nombre, overwrites=overwrites)
    await ctx.send(f'🔒 Canal secreto de texto creado: {canal.mention}')

@secret.command()
async def voice(ctx, nombre: str, *, usuarios_roles: str):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    for name in usuarios_roles.split():
        role_or_user = discord.utils.get(ctx.guild.roles, name=name) or discord.utils.get(ctx.guild.members, name=name)
        if role_or_user:
            overwrites[role_or_user] = discord.PermissionOverwrite(view_channel=True)
    canal = await ctx.guild.create_voice_channel(nombre, overwrites=overwrites)
    await ctx.send(f'🔒 Canal secreto de voz creado: {canal.mention}')

@secret.command()
async def emoji(ctx, nombre: str, *, roles: str):
    if not ctx.message.attachments:
        await ctx.send("⚠️ Adjunta una imagen para el emoji.")
        return
    imagen = await ctx.message.attachments[0].read()
    emoji = await ctx.guild.create_custom_emoji(name=nombre, image=imagen)
    await ctx.send(f'😎 Emoji creado: <:{emoji.name}:{emoji.id}> solo para roles: {roles}')

@bot.command()
async def mem(ctx):
    img_name = random.choice(os.listdir('images'))
    # ¡Y así es como se puede sustituir el nombre del fichero desde una variable!
    with open(f'images/{img_name}', 'rb') as f:
        picture = discord.File(f)
        await ctx.send(file=picture)

def get_duck_image_url():    
    url = 'https://random-d.uk/api/random'
    res = requests.get(url)
    data = res.json()
    return data['url']


@bot.command('duck')
async def duck(ctx):
    '''Una vez que llamamos al comando duck, 
    el programa llama a la función get_duck_image_url'''
    image_url = get_duck_image_url()
    await ctx.send(image_url)

# --- Evento on_ready y arranque del bot ---
@bot.event
async def on_ready():
    await bot.add_cog(Music(bot))
    print(f'✅ Bot listo como {bot.user} (ID: {bot.user.id})')



bot.run('TU TOKEN AQUI')
