import discord
from discord.ext import commands
import random
import yt_dlp as youtube_dl
import asyncio
import secrets
import string
import os
import requests
import re

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
async def mem(ctx, categoria: str = None):
    base_path = 'images'
    
    if categoria is None:
        categorias = [name for name in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, name))]
        await ctx.send(f"📂 Categorías disponibles: {', '.join(categorias)}")
        return

    categoria_path = os.path.join(base_path, categoria.lower())
    if not os.path.exists(categoria_path) or not os.path.isdir(categoria_path):
        await ctx.send("⚠️ Categoría no encontrada. Usa `/mem` para ver las disponibles.")
        return

    archivos = os.listdir(categoria_path)
    if not archivos:
        await ctx.send("⚠️ No hay memes en esta categoría.")
        return

    imagen_aleatoria = random.choice(archivos)
    with open(os.path.join(categoria_path, imagen_aleatoria), 'rb') as f:
        await ctx.send(file=discord.File(f))

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

@bot.command()
async def traducir(ctx, idioma: str, *, texto: str):
    urls = [
        "https://libretranslate.de/translate",
        "https://translate.argosopentech.com/translate"
    ]

    payload = {
        "q": texto,
        "source": "auto",
        "target": idioma.lower(),
        "format": "text"
    }

    for url in urls:
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                try:
                    data = response.json()
                    traduccion = data.get("translatedText")
                    if traduccion:
                        await ctx.send(f"🌍 Traducción a **{idioma}**:\n👉 {traduccion}")
                        return
                except Exception:
                    continue  # Prueba el siguiente servidor si falla el JSON
        except requests.exceptions.RequestException:
            continue

    await ctx.send("❌ No se pudo traducir el texto. Intenta más tarde.")

@bot.command()
async def idiomas(ctx):
    urls = [
        "https://libretranslate.de/languages",
        "https://translate.argosopentech.com/languages"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                try:
                    data = response.json()
                    lista = [f"{lang['name']} ({lang['code']})" for lang in data]
                    mensaje = "🌐 Idiomas disponibles:\n" + "\n".join(lista)
                    await ctx.send(mensaje)
                    return
                except Exception:
                    continue  # Prueba el siguiente servidor si falla el JSON
        except requests.exceptions.RequestException:
            continue

    await ctx.send("❌ No se pudo obtener la lista de idiomas desde ningún servidor.")

@bot.command()
async def recordar(ctx, tiempo: str, *, mensaje: str):
    # Expresión para detectar formato como "10s", "5m", "2h"
    patron = r"^(\d+)([smh])$"
    match = re.match(patron, tiempo.lower())

    if not match:
        await ctx.send("⚠️ Usa un formato de tiempo válido: 10s, 5m, 2h.")
        return

    cantidad, unidad = match.groups()
    cantidad = int(cantidad)

    # Convertir a segundos
    segundos = cantidad
    if unidad == 'm':
        segundos *= 60
    elif unidad == 'h':
        segundos *= 3600

    await ctx.send(f"⏰ Te recordaré en {cantidad}{unidad}: **{mensaje}**")

    await asyncio.sleep(segundos)
    await ctx.send(f"🔔 ¡Recordatorio! {ctx.author.mention}: **{mensaje}**")

# --- Menú de Preguntas Específicas ---
class PreguntasView(discord.ui.View):
    def __init__(self, ctx, tema, timeout=120):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.tema = tema
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("⚠️ No puedes usar este menú.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="¿Qué es?", style=discord.ButtonStyle.primary, row=0)
    async def que_es(self, interaction: discord.Interaction, button: discord.ui.Button):
        respuestas = {
            "Reciclaje": "♻️ El reciclaje es el proceso de recolectar y procesar materiales que de otro modo serían desechados como basura y convertirlos en nuevos productos.",
            "Calentamiento Global": "🌍 El calentamiento global es el aumento gradual de la temperatura de la Tierra debido a la acumulación de gases de efecto invernadero en la atmósfera.",
            "Deforestación": "🌳 La deforestación es la tala o eliminación de bosques y selvas, normalmente para dar paso a actividades humanas como la agricultura o construcción."
        }
        await interaction.response.send_message(respuestas[self.tema], ephemeral=True)

    @discord.ui.button(label="¿Qué hace?", style=discord.ButtonStyle.success, row=1)
    async def que_hace(self, interaction: discord.Interaction, button: discord.ui.Button):
        respuestas = {
            "Reciclaje": "♻️ El reciclaje reduce la cantidad de residuos enviados a vertederos e incineradoras, conserva recursos naturales y ahorra energía.",
            "Calentamiento Global": "🌍 El calentamiento global provoca cambios climáticos extremos, aumento del nivel del mar y pérdida de biodiversidad.",
            "Deforestación": "🌳 La deforestación destruye hábitats, contribuye al cambio climático y reduce la biodiversidad."
        }
        await interaction.response.send_message(respuestas[self.tema], ephemeral=True)

    @discord.ui.button(label="¿Es bueno?", style=discord.ButtonStyle.secondary, row=2)
    async def es_bueno(self, interaction: discord.Interaction, button: discord.ui.Button):
        respuestas = {
            "Reciclaje": "✅ Sí, el reciclaje es bueno para el medio ambiente y la economía circular.",
            "Calentamiento Global": "❌ No, el calentamiento global es perjudicial para todos los ecosistemas y la vida humana.",
            "Deforestación": "❌ No, la deforestación causa daños ambientales graves y a largo plazo."
        }
        await interaction.response.send_message(respuestas[self.tema], ephemeral=True)

    @discord.ui.button(label="Salir", style=discord.ButtonStyle.danger, row=3)
    async def salir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🚪 Menú de **{self.tema}** cerrado.", ephemeral=True)
        self.stop()


# --- Menú Inicial ---
class ContaminacionView(discord.ui.View):
    def __init__(self, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("⚠️ No puedes usar este menú.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def cambiar_a_preguntas(self, interaction, tema):
        view = PreguntasView(self.ctx, tema)
        view.message = await interaction.response.edit_message(content=f"📚 **{tema}** - Elige una pregunta:", view=view)

    @discord.ui.button(label="Reciclaje", style=discord.ButtonStyle.success, row=0)
    async def reciclaje(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cambiar_a_preguntas(interaction, "Reciclaje")

    @discord.ui.button(label="Calentamiento Global", style=discord.ButtonStyle.primary, row=1)
    async def calentamiento_global(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cambiar_a_preguntas(interaction, "Calentamiento Global")

    @discord.ui.button(label="Deforestación", style=discord.ButtonStyle.secondary, row=2)
    async def deforestacion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cambiar_a_preguntas(interaction, "Deforestación")

    @discord.ui.button(label="Salir", style=discord.ButtonStyle.danger, row=3)
    async def salir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚪 Menú cerrado.", ephemeral=True)
        self.stop()

@bot.command(name="comandos")
async def comandos(ctx):
    embed = discord.Embed(
        title="📜 Lista de Comandos",
        description="Aquí tienes todos los comandos organizados por categorías:",
        color=discord.Color.green()
    )

    # 🎵 Música
    embed.add_field(
        name="🎵 Música",
        value=(
            "`/join <canal>` → El bot se une a un canal de voz.\n"
            "`/play <ruta>` → Reproduce un archivo de audio.\n"
            "`/yt <URL>` → Reproduce audio desde un video de YouTube.\n"
            "`/stream <URL>` → Transmite audio en vivo desde YouTube.\n"
            "`/volume <0-100>` → Ajusta el volumen.\n"
            "`/stop` → Desconecta al bot del canal de voz."
        ),
        inline=False
    )

    # 🎲 Juegos y utilidades
    embed.add_field(
        name="🎲 Juegos y Utilidades",
        value=(
            "`/dado` → Lanza un dado de 6 caras.\n"
            "`/roll NdN` → Lanza dados personalizados (ej: 2d6).\n"
            "`/choose <op1> <op2> ...` → Elige aleatoriamente entre opciones.\n"
            "`/repetir <texto>` → Repite el texto indicado.\n"
            "`/repeat <n> <texto>` → Repite el texto n veces."
        ),
        inline=False
    )

    # 🔑 Seguridad y contraseñas
    embed.add_field(
        name="🔑 Seguridad",
        value=(
            "`/generar_password` → Genera una contraseña segura de 12 caracteres.\n"
            "`/password <longitud>` → Genera una contraseña segura de la longitud indicada."
        ),
        inline=False
    )

    # 📅 Información de usuarios
    embed.add_field(
        name="📅 Información",
        value=(
            "`/joined <usuario>` → Muestra cuándo se unió el usuario.\n"
            "`/cool <texto>` → Responde si el texto es cool."
        ),
        inline=False
    )

    # 🔒 Comandos secretos
    embed.add_field(
        name="🔒 Comandos Secretos",
        value=(
            "`/secret text <nombre> <usuarios/roles>` → Crea un canal de texto privado.\n"
            "`/secret voice <nombre> <usuarios/roles>` → Crea un canal de voz privado.\n"
            "`/secret emoji <nombre> <roles>` → Crea un emoji privado."
        ),
        inline=False
    )

    # 🌍 Traducción y lenguajes
    embed.add_field(
        name="🌍 Traducción",
        value=(
            "`/traducir <idioma> <texto>` → Traduce el texto al idioma indicado.\n"
            "`/idiomas` → Muestra idiomas disponibles para traducir."
        ),
        inline=False
    )

    # 🖼️ Imágenes y memes
    embed.add_field(
        name="🖼️ Imágenes y Memes",
        value=(
            "`/mem <categoría>` → Envía un meme de la categoría.\n"
            "`/duck` → Manda una imagen aleatoria de un pato."
        ),
        inline=False
    )

    # ⏰ Recordatorios
    embed.add_field(
        name="⏰ Recordatorios",
        value=(
            "`/recordar <tiempo> <mensaje>` → Envía un recordatorio después del tiempo indicado (ej: 10s, 5m, 2h)."
        ),
        inline=False
    )

    # 🌱 Educación ambiental
    embed.add_field(
        name="🌱 Educación Ambiental",
        value=(
            "`/Contaminacion` → Muestra un menú interactivo con temas sobre contaminación."
        ),
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name="Contaminacion")
async def contaminacion(ctx):
    view = ContaminacionView(ctx, timeout=60)
    view.message = await ctx.send("🌱 **Elige un tema sobre contaminación:**", view=view)  

# --- Evento on_ready y arranque del bot ---
@bot.event
async def on_ready():
    await bot.add_cog(Music(bot))
    print(f'✅ Bot listo como {bot.user} (ID: {bot.user.id})')

bot.run('TU TOKEN AQUI')
