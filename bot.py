import asyncio
import json
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


# ==============================
# CONFIG
# ==============================

with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

TOKEN = config["token"]
GUILD_ID = config["guild_id"]
STAFF_ROLE_ID = config["staff_role_id"]
OWNER_IDS = config["owner_ids"]


# ==============================
# INTENTS
# ==============================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# ==============================
# BOT
# ==============================

bot = commands.Bot(
    command_prefix="/",
    intents=intents
)

GUILD = discord.Object(id=GUILD_ID)

target_type = None
target_id = None


# ==============================
# YETKİ
# ==============================

def is_authorized(member: discord.Member):
    if member.id in OWNER_IDS:
        return True

    return any(
        role.id == STAFF_ROLE_ID
        for role in member.roles
    )


async def check_permission(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        return False

    if is_authorized(interaction.user):
        return True

    await interaction.response.send_message(
        "❌ Bu komutu kullanma yetkin yok.",
        ephemeral=True
    )
    return False


# ==============================
# BOT HAZIR
# ==============================

@bot.event
async def on_ready():
    await bot.tree.sync(guild=GUILD)

    print("")
    print("================================")
    print("       TSLK BOT AKTİF")
    print("================================")
    print(f"Bot: {bot.user}")
    print(f"ID: {bot.user.id}")
    print("Slash komutları hazır.")
    print("================================")
    print("")


# ==============================
# DM MESAJLARINI GÖSTER
# ==============================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        print("")
        print("================================")
        print("📩 YENİ DM")
        print("================================")
        print(f"Kullanıcı : {message.author}")
        print(f"ID        : {message.author.id}")
        print(f"Mesaj     : {message.content}")
        print("================================")
        print("")

    await bot.process_commands(message)


# ==============================
# PING
# ==============================

@bot.tree.command(
    name="ping",
    description="Botun çalışıp çalışmadığını kontrol eder.",
    guild=GUILD
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")


# ==============================
# YETKİ TEST
# ==============================

@bot.tree.command(
    name="yetki-test",
    description="Yetkini kontrol eder.",
    guild=GUILD
)
async def yetki_test(interaction: discord.Interaction):
    if not await check_permission(interaction):
        return

    if interaction.user.id in OWNER_IDS:
        await interaction.response.send_message(
            "👑 Bot Owner\nTam yetkin var."
        )
    else:
        await interaction.response.send_message(
            "🛡️ Yetkili rolüne sahipsin."
        )


# ==============================
# BAN
# ==============================

@bot.tree.command(
    name="ban",
    description="Kullanıcıyı banlar.",
    guild=GUILD
)
@app_commands.describe(
    user="Banlanacak kullanıcı",
    reason="Ban sebebi"
)
async def ban(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ Botun Ban Members yetkisi yok.",
            ephemeral=True
        )
        return

    if user.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Bu kullanıcıyı banlayamam.",
            ephemeral=True
        )
        return

    try:
        await user.ban(reason=reason)

        await interaction.response.send_message(
            f"🔨 **{user}** banlandı.\n"
            f"Sebep: {reason}"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Ban işlemi başarısız.",
            ephemeral=True
        )


# ==============================
# PERMBAN
# ==============================

@bot.tree.command(
    name="permban",
    description="Kullanıcıyı kalıcı olarak banlar.",
    guild=GUILD
)
@app_commands.describe(
    user="Banlanacak kullanıcı",
    reason="Ban sebebi"
)
async def permban(
    interaction: discord.Interaction,
    user: discord.User,
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ Botun Ban Members yetkisi yok.",
            ephemeral=True
        )
        return

    try:
        await interaction.guild.ban(
            user,
            reason=f"PERMBAN | {reason}"
        )

        await interaction.response.send_message(
            f"⛔ **PERMBAN**\n"
            f"**Kullanıcı:** {user}\n"
            f"**ID:** `{user.id}`\n"
            f"**Sebep:** {reason}"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Permaban başarısız.",
            ephemeral=True
        )


# ==============================
# KICK
# ==============================

@bot.tree.command(
    name="kick",
    description="Kullanıcıyı sunucudan atar.",
    guild=GUILD
)
@app_commands.describe(
    user="Atılacak kullanıcı",
    reason="Sebep"
)
async def kick(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    if not interaction.guild.me.guild_permissions.kick_members:
        await interaction.response.send_message(
            "❌ Botun Kick Members yetkisi yok.",
            ephemeral=True
        )
        return

    if user.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Bu kullanıcıyı atamam.",
            ephemeral=True
        )
        return

    try:
        await user.kick(reason=reason)

        await interaction.response.send_message(
            f"👢 **{user}** atıldı.\n"
            f"Sebep: {reason}"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Kick başarısız.",
            ephemeral=True
        )


# ==============================
# MUTE
# ==============================

@bot.tree.command(
    name="mute",
    description="Kullanıcıya timeout uygular.",
    guild=GUILD
)
@app_commands.describe(
    user="Mute uygulanacak kullanıcı",
    minutes="Dakika",
    reason="Sebep"
)
async def mute(
    interaction: discord.Interaction,
    user: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    if not interaction.guild.me.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ Botun Moderate Members yetkisi yok.",
            ephemeral=True
        )
        return

    try:
        await user.timeout(
            timedelta(minutes=minutes),
            reason=reason
        )

        await interaction.response.send_message(
            f"🔇 **{user}** mutelendi.\n"
            f"Süre: {minutes} dakika\n"
            f"Sebep: {reason}"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Mute başarısız.",
            ephemeral=True
        )


# ==============================
# UNMUTE
# ==============================

@bot.tree.command(
    name="unmute",
    description="Kullanıcının timeoutunu kaldırır.",
    guild=GUILD
)
@app_commands.describe(
    user="Mute kaldırılacak kullanıcı",
    reason="Sebep"
)
async def unmute(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    if not interaction.guild.me.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ Botun Moderate Members yetkisi yok.",
            ephemeral=True
        )
        return

    try:
        await user.timeout(None, reason=reason)

        await interaction.response.send_message(
            f"🔊 **{user}** unmute edildi.\n"
            f"Sebep: {reason}"
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Unmute başarısız.",
            ephemeral=True
        )


# ==============================
# TERMINAL
# ==============================

async def terminal():
    global target_type
    global target_id

    await bot.wait_until_ready()

    print("")
    print("================================")
    print("       TSLK BOT TERMINAL")
    print("================================")
    print("kanal ID  -> Kanal hedefi")
    print("dm ID     -> DM hedefi")
    print("> mesaj   -> Mesaj gönder")
    print("hedef     -> Hedefi göster")
    print("yardım    -> Yardım")
    print("================================")
    print("")

    while not bot.is_closed():
        try:
            text = await asyncio.to_thread(input, ">>> ")
            text = text.strip()

            if not text:
                continue

            if text.lower().startswith("kanal "):
                value = text[6:].strip()

                try:
                    channel_id = int(value)
                except ValueError:
                    print("❌ Geçerli kanal ID gir.")
                    continue

                channel = bot.get_channel(channel_id)

                if channel is None:
                    print("❌ Kanal bulunamadı.")
                    continue

                target_type = "channel"
                target_id = channel_id

                print(f"✅ Kanal hedefi: #{channel.name}")
                continue

            if text.lower().startswith("dm "):
                value = text[3:].strip()

                try:
                    user_id = int(value)
                except ValueError:
                    print("❌ Geçerli kullanıcı ID gir.")
                    continue

                try:
                    user = await bot.fetch_user(user_id)
                except discord.NotFound:
                    print("❌ Kullanıcı bulunamadı.")
                    continue

                target_type = "dm"
                target_id = user_id

                print(f"✅ DM hedefi: {user} ({user.id})")
                continue

            if text.startswith(">"):
                content = text[1:].strip()

                if not content:
                    print("❌ Mesaj boş olamaz.")
                    continue

                if target_type is None:
                    print("❌ Önce kanal veya DM seç.")
                    continue

                if target_type == "channel":
                    channel = bot.get_channel(target_id)

                    if channel is None:
                        print("❌ Kanal bulunamadı.")
                        continue

                    try:
                        await channel.send(content)
                        print(
                            f"✅ #{channel.name} kanalına gönderildi."
                        )
                    except discord.Forbidden:
                        print(
                            "❌ Mesaj gönderme yetkisi yok."
                        )

                elif target_type == "dm":
                    try:
                        user = await bot.fetch_user(target_id)
                        await user.send(content)
                        print(
                            f"✅ {user} kişisine DM gönderildi."
                        )
                    except discord.Forbidden:
                        print(
                            "❌ Bu kişiye DM gönderilemiyor."
                        )
                    except discord.HTTPException as error:
                        print(f"❌ Discord hatası: {error}")

                continue

            if text.lower() == "hedef":
                if target_type is None:
                    print("🎯 Hedef seçilmedi.")

                elif target_type == "channel":
                    channel = bot.get_channel(target_id)

                    if channel:
                        print(f"🎯 Kanal: #{channel.name}")
                    print(f"🆔 {target_id}")

                elif target_type == "dm":
                    try:
                        user = await bot.fetch_user(target_id)
                        print(f"🎯 DM: {user}")
                        print(f"🆔 {target_id}")
                    except Exception:
                        print(f"🎯 DM ID: {target_id}")

                continue

            if text.lower() == "yardım":
                print("")
                print("kanal ID")
                print("→ Kanal seçer.")
                print("")
                print("dm ID")
                print("→ DM kişisi seçer.")
                print("")
                print("> mesaj")
                print("→ Seçilen hedefe mesaj gönderir.")
                print("")
                print("hedef")
                print("→ Mevcut hedefi gösterir.")
                print("")
                continue

            print("❌ Bilinmeyen komut.")

        except Exception as error:
            print(f"❌ Terminal hatası: {error}")


# ==============================
# BAŞLAT
# ==============================

async def main():
    terminal_task = asyncio.create_task(terminal())

    try:
        await bot.start(TOKEN)
    finally:
        terminal_task.cancel()


asyncio.run(main())
