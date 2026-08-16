import asyncio
import json
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# CONFIG
# =========================================================

with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

TOKEN = config["token"]
GUILD_ID = config["guild_id"]
STAFF_ROLE_ID = config["staff_role_id"]
OWNER_IDS = config["owner_ids"]


# =========================================================
# BOT
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="/",
    intents=intents
)

GUILD = discord.Object(id=GUILD_ID)


# =========================================================
# YETKİ SİSTEMİ
# =========================================================

def is_authorized(member: discord.Member) -> bool:

    # Bot Owner
    if member.id in OWNER_IDS:
        return True

    # Yetkili rolü
    return any(
        role.id == STAFF_ROLE_ID
        for role in member.roles
    )


async def check_permission(
    interaction: discord.Interaction
) -> bool:

    if not isinstance(interaction.user, discord.Member):
        return False

    if is_authorized(interaction.user):
        return True

    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ Bu komutu kullanma yetkin yok.",
            ephemeral=True
        )

    return False


# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():

    await bot.tree.sync(guild=GUILD)

    print("----------------------------------------")
    print(f"Bot giriş yaptı: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Slash komutları senkronize edildi.")
    print("----------------------------------------")


# =========================================================
# PING
# =========================================================

@bot.tree.command(
    name="ping",
    description="Botun çalışıp çalışmadığını kontrol eder.",
    guild=GUILD
)
async def ping(interaction: discord.Interaction):

    await interaction.response.send_message(
        "🏓 Pong!"
    )


# =========================================================
# YETKİ TEST
# =========================================================

@bot.tree.command(
    name="yetki-test",
    description="Bot üzerindeki yetkini kontrol eder.",
    guild=GUILD
)
async def yetki_test(interaction: discord.Interaction):

    if not await check_permission(interaction):
        return

    if interaction.user.id in OWNER_IDS:

        await interaction.response.send_message(
            "👑 **Bot Owner**\n"
            "Bot üzerinde tam yetkin var."
        )

    else:

        await interaction.response.send_message(
            "🛡️ **Yetkili**\n"
            "Belirlenen yetkili rolüne sahipsin."
        )


# =========================================================
# BAN
# =========================================================

@bot.tree.command(
    name="ban",
    description="Bir kullanıcıyı sunucudan yasaklar.",
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
            "❌ Botun **Ban Members** yetkisi yok.",
            ephemeral=True
        )
        return

    if user == interaction.user:

        await interaction.response.send_message(
            "❌ Kendini banlayamazsın.",
            ephemeral=True
        )
        return

    if user.top_role >= interaction.guild.me.top_role:

        await interaction.response.send_message(
            "❌ Bu kullanıcıyı banlayamam. "
            "Kullanıcının rolü botun rolüne eşit veya daha yüksek.",
            ephemeral=True
        )
        return

    try:

        await user.ban(
            reason=f"{reason} | Yetkili: {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔨 **{user}** banlandı.\n"
            f"**Sebep:** {reason}\n"
            f"**Yetkili:** {interaction.user.mention}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Discord botun bu kullanıcıyı banlamasına izin vermedi.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.response.send_message(
            "❌ Ban işlemi sırasında Discord API hatası oluştu.",
            ephemeral=True
        )


# =========================================================
# PERMBAN
# =========================================================

@bot.tree.command(
    name="permban",
    description="Bir kullanıcıyı kalıcı olarak yasaklar.",
    guild=GUILD
)
@app_commands.describe(
    user="Kalıcı olarak banlanacak kullanıcı",
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
            "❌ Botun **Ban Members** yetkisi yok.",
            ephemeral=True
        )
        return

    member = interaction.guild.get_member(user.id)

    if member:

        if member.top_role >= interaction.guild.me.top_role:

            await interaction.response.send_message(
                "❌ Bu kullanıcıyı banlayamam. "
                "Kullanıcının rolü botun rolüne eşit veya daha yüksek.",
                ephemeral=True
            )
            return

    try:

        await interaction.guild.ban(
            user,
            reason=f"PERMBAN | {reason} | Yetkili: {interaction.user}"
        )

        await interaction.response.send_message(
            f"⛔ **PERMBAN**\n\n"
            f"**Kullanıcı:** {user}\n"
            f"**ID:** `{user.id}`\n"
            f"**Sebep:** {reason}\n"
            f"**Yetkili:** {interaction.user.mention}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Discord botun bu kullanıcıyı banlamasına izin vermedi.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.response.send_message(
            "❌ Permaban sırasında hata oluştu.",
            ephemeral=True
        )


# =========================================================
# KICK
# =========================================================

@bot.tree.command(
    name="kick",
    description="Bir kullanıcıyı sunucudan atar.",
    guild=GUILD
)
@app_commands.describe(
    user="Atılacak kullanıcı",
    reason="Atılma sebebi"
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
            "❌ Botun **Kick Members** yetkisi yok.",
            ephemeral=True
        )
        return

    if user == interaction.user:

        await interaction.response.send_message(
            "❌ Kendini atamazsın.",
            ephemeral=True
        )
        return

    if user.top_role >= interaction.guild.me.top_role:

        await interaction.response.send_message(
            "❌ Bu kullanıcıyı atamam. "
            "Kullanıcının rolü botun rolüne eşit veya daha yüksek.",
            ephemeral=True
        )
        return

    try:

        await user.kick(
            reason=f"{reason} | Yetkili: {interaction.user}"
        )

        await interaction.response.send_message(
            f"👢 **{user}** sunucudan atıldı.\n"
            f"**Sebep:** {reason}\n"
            f"**Yetkili:** {interaction.user.mention}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Discord botun bu kullanıcıyı atmasına izin vermedi.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.response.send_message(
            "❌ Kick işlemi sırasında hata oluştu.",
            ephemeral=True
        )


# =========================================================
# MUTE
# =========================================================

@bot.tree.command(
    name="mute",
    description="Bir kullanıcıya timeout uygular.",
    guild=GUILD
)
@app_commands.describe(
    user="Mute uygulanacak kullanıcı",
    minutes="Mute süresi (dakika)",
    reason="Mute sebebi"
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
            "❌ Botun **Moderate Members** yetkisi yok.",
            ephemeral=True
        )
        return

    if user == interaction.user:

        await interaction.response.send_message(
            "❌ Kendini mute edemezsin.",
            ephemeral=True
        )
        return

    if user.top_role >= interaction.guild.me.top_role:

        await interaction.response.send_message(
            "❌ Bu kullanıcıya mute uygulayamam. "
            "Kullanıcının rolü botun rolüne eşit veya daha yüksek.",
            ephemeral=True
        )
        return

    try:

        duration = timedelta(minutes=minutes)

        await user.timeout(
            duration,
            reason=f"{reason} | Yetkili: {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔇 **{user}** mutelandı.\n"
            f"**Süre:** {minutes} dakika\n"
            f"**Sebep:** {reason}\n"
            f"**Yetkili:** {interaction.user.mention}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Discord botun bu kullanıcıya timeout uygulamasına izin vermedi.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.response.send_message(
            "❌ Mute işlemi sırasında hata oluştu.",
            ephemeral=True
        )


# =========================================================
# UNMUTE
# =========================================================

@bot.tree.command(
    name="unmute",
    description="Bir kullanıcının timeoutunu kaldırır.",
    guild=GUILD
)
@app_commands.describe(
    user="Mute kaldırılacak kullanıcı",
    reason="Mute kaldırma sebebi"
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
            "❌ Botun **Moderate Members** yetkisi yok.",
            ephemeral=True
        )
        return

    try:

        await user.timeout(
            None,
            reason=f"{reason} | Yetkili: {interaction.user}"
        )

        await interaction.response.send_message(
            f"🔊 **{user}** kullanıcısının mute'u kaldırıldı.\n"
            f"**Sebep:** {reason}\n"
            f"**Yetkili:** {interaction.user.mention}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Discord botun timeout kaldırmasına izin vermedi.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.response.send_message(
            "❌ Unmute işlemi sırasında hata oluştu.",
            ephemeral=True
        )


# =========================================================
# TERMINAL
# =========================================================

async def terminal():

    await bot.wait_until_ready()

    print("")
    print("========================================")
    print("           TSLK BOT TERMINAL")
    print("========================================")
    print("kanal ID   -> Mesaj kanalını değiştir")
    print("> mesaj    -> Mesaj gönder")
    print("durum      -> Mevcut kanalı göster")
    print("yardım     -> Komutları göster")
    print("========================================")
    print("")

    while not bot.is_closed():

        try:
            text = await asyncio.to_thread(
                input,
                ">>> "
            )

            text = text.strip()

            if not text:
                continue

            # =====================================
            # KANAL DEĞİŞTİR
            # =====================================

            if text.lower().startswith("kanal "):

                channel_id_text = text[6:].strip()

                try:
                    channel_id = int(channel_id_text)

                except ValueError:
                    print("❌ Geçerli bir kanal ID gir.")
                    continue

                channel = bot.get_channel(channel_id)

                if channel is None:
                    print("❌ Kanal bulunamadı.")
                    continue

                config["terminal_channel_id"] = channel_id

                print(
                    f"✅ Mesaj kanalı değiştirildi: "
                    f"#{channel.name}"
                )

                continue

            # =====================================
            # MESAJ GÖNDER
            # =====================================

            if text.startswith(">"):

                message = text[1:].strip()

                if not message:
                    print("❌ Mesaj boş olamaz.")
                    continue

                channel_id = config.get(
                    "terminal_channel_id"
                )

                if not channel_id:
                    print(
                        "❌ Önce bir kanal seçmelisin."
                    )
                    continue

                channel = bot.get_channel(channel_id)

                if channel is None:
                    print("❌ Kanal bulunamadı.")
                    continue

                try:
                    await channel.send(message)

                    print(
                        f"✅ #{channel.name} kanalına "
                        f"mesaj gönderildi."
                    )

                except discord.Forbidden:
                    print(
                        "❌ Botun bu kanala mesaj gönderme "
                        "yetkisi yok."
                    )

                except discord.HTTPException as error:
                    print(
                        f"❌ Discord mesaj gönderme hatası: "
                        f"{error}"
                    )

                continue

            # =====================================
            # DURUM
            # =====================================

            if text.lower() == "durum":

                channel_id = config.get(
                    "terminal_channel_id"
                )

                if not channel_id:
                    print(
                        "❌ Henüz bir kanal seçilmedi."
                    )
                    continue

                channel = bot.get_channel(channel_id)

                if channel:
                    print(
                        f"📢 Mevcut kanal: "
                        f"#{channel.name}"
                    )
                else:
                    print(
                        f"📢 Kanal ID: {channel_id}"
                    )

                continue

            # =====================================
            # YARDIM
            # =====================================

            if text.lower() == "yardım":

                print("")
                print(
                    "kanal ID   -> Mesaj kanalını değiştir"
                )
                print(
                    "> mesaj    -> Mesaj gönder"
                )
                print(
                    "durum      -> Mevcut kanalı göster"
                )
                print(
                    "yardım     -> Yardım"
                )
                print("")

                continue

            print(
                "❌ Bilinmeyen komut. "
                "'yardım' yazabilirsin."
            )

        except Exception as error:

            print(f"❌ Terminal hatası: {error}")

# =========================================================
# BAŞLAT
# =========================================================

async def main():

    terminal_task = asyncio.create_task(
        terminal()
    )

    try:

        await bot.start(TOKEN)

    finally:

        terminal_task.cancel()


asyncio.run(main())
