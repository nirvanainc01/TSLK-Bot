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
ROLE_LOG_CHANNEL_ID = config.get("role_log_channel_id", 0)


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
# ENGELLENEN KULLANICILAR
# ==============================

BLOCKED_USERS_FILE = "blocked_users.json"

try:
    with open(BLOCKED_USERS_FILE, "r", encoding="utf-8") as file:
        BLOCKED_USER_IDS = set(int(user_id) for user_id in json.load(file))
except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
    BLOCKED_USER_IDS = set()


def save_blocked_users():
    with open(BLOCKED_USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(sorted(BLOCKED_USER_IDS), file, ensure_ascii=False, indent=4)


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

    # Engelli kullanıcı sunucuda mesaj yazarsa mesajını sil.
    if (
        message.guild is not None
        and message.author.id in BLOCKED_USER_IDS
    ):
        try:
            await message.delete()
            print(
                f"🗑️ Engelli kullanıcının mesajı silindi: "
                f"{message.author} ({message.author.id})"
            )
        except discord.Forbidden:
            print(
                f"❌ Mesaj silinemedi. Botun Manage Messages yetkisi yok: "
                f"#{getattr(message.channel, 'name', 'bilinmeyen')}"
            )
        except discord.HTTPException as error:
            print(f"❌ Mesaj silme hatası: {error}")

        return

    # DM mesajlarını terminalde göster.
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
# SES KANALI KORUMASI
# ==============================

@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState
):
    if member.bot:
        return

    # Engelli kullanıcı sese girdiyse veya başka bir ses kanalına geçtiyse çıkar.
    if member.id in BLOCKED_USER_IDS and after.channel is not None:
        try:
            await member.move_to(
                None,
                reason="Engellenen kullanıcı ses kanalına girdi."
            )
            print(
                f"🔇 Engelli kullanıcı sesten atıldı: "
                f"{member} ({member.id})"
            )
        except discord.Forbidden:
            print(
                "❌ Kullanıcı sesten atılamadı. "
                "Botun Move Members yetkisi yok."
            )
        except discord.HTTPException as error:
            print(f"❌ Ses kanalından çıkarma hatası: {error}")


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
# ROL VER
# ==============================

@bot.tree.command(
    name="rol-ver",
    description="Bir kullanıcıya rol verir.",
    guild=GUILD
)
@app_commands.describe(
    user="Rol verilecek kişi",
    role="Verilecek rol",
    reason="Rol verme sebebi"
)
async def rol_ver(
    interaction: discord.Interaction,
    user: discord.Member,
    role: discord.Role,
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    me = interaction.guild.me

    if me is None:
        await interaction.response.send_message(
            "❌ Bot sunucudaki kendi üyesini bulamadı.",
            ephemeral=True
        )
        return

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ Bu rol verilemez.",
            ephemeral=True
        )
        return

    if role >= me.top_role:
        await interaction.response.send_message(
            "❌ Botun rolü, verilecek rolden daha yukarıda olmalı.",
            ephemeral=True
        )
        return

    if user.top_role >= me.top_role:
        await interaction.response.send_message(
            "❌ Bu kullanıcıya rol veremem; kullanıcı botun rolüne eşit veya daha yüksek bir role sahip.",
            ephemeral=True
        )
        return

    if role in user.roles:
        await interaction.response.send_message(
            f"ℹ️ {user.mention} kullanıcısında **{role.name}** rolü zaten var.",
            ephemeral=True
        )
        return

    try:
        await user.add_roles(
            role,
            reason=f"{reason} | Yetkili: {interaction.user} ({interaction.user.id})"
        )

        await interaction.response.send_message(
            f"✅ {user.mention} kullanıcısına **{role.name}** rolü verildi.\n"
            f"**Sebep:** {reason}"
        )

        if ROLE_LOG_CHANNEL_ID:
            log_channel = bot.get_channel(ROLE_LOG_CHANNEL_ID)

            if log_channel is not None:
                embed = discord.Embed(
                    title="🟢 Rol Verildi",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(
                    name="Kullanıcı",
                    value=f"{user.mention}\n`{user.id}`",
                    inline=True
                )
                embed.add_field(
                    name="Rol",
                    value=f"{role.mention}\n`{role.id}`",
                    inline=True
                )
                embed.add_field(
                    name="Yetkili",
                    value=f"{interaction.user.mention}\n`{interaction.user.id}`",
                    inline=False
                )
                embed.add_field(
                    name="Sebep",
                    value=reason,
                    inline=False
                )

                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    print(
                        f"❌ Rol log kanalına mesaj gönderilemiyor: "
                        f"{ROLE_LOG_CHANNEL_ID}"
                    )
            else:
                print(
                    f"❌ Rol log kanalı bulunamadı: "
                    f"{ROLE_LOG_CHANNEL_ID}"
                )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Botun bu rolü verme yetkisi yok.",
            ephemeral=True
        )
    except discord.HTTPException as error:
        await interaction.response.send_message(
            f"❌ Rol verme sırasında Discord hatası oluştu: {error}",
            ephemeral=True
        )


# ==============================
# ROL AL
# ==============================

@bot.tree.command(
    name="rol-al",
    description="Bir kullanıcıdan rol alır.",
    guild=GUILD
)
@app_commands.describe(
    user="Rolü alınacak kişi",
    role="Alınacak rol",
    reason="Rol alma sebebi"
)
async def rol_al(
    interaction: discord.Interaction,
    user: discord.Member,
    role: discord.Role,
    reason: str = "Sebep belirtilmedi."
):
    if not await check_permission(interaction):
        return

    me = interaction.guild.me

    if me is None:
        await interaction.response.send_message(
            "❌ Bot sunucudaki kendi üyesini bulamadı.",
            ephemeral=True
        )
        return

    if role.is_default() or role.managed:
        await interaction.response.send_message(
            "❌ Bu rol alınamaz.",
            ephemeral=True
        )
        return

    if role >= me.top_role:
        await interaction.response.send_message(
            "❌ Botun rolü, alınacak rolden daha yukarıda olmalı.",
            ephemeral=True
        )
        return

    if role not in user.roles:
        await interaction.response.send_message(
            f"ℹ️ {user.mention} kullanıcısında **{role.name}** rolü yok.",
            ephemeral=True
        )
        return

    try:
        await user.remove_roles(
            role,
            reason=f"{reason} | Yetkili: {interaction.user} ({interaction.user.id})"
        )

        await interaction.response.send_message(
            f"✅ {user.mention} kullanıcısından **{role.name}** rolü alındı.\n"
            f"**Sebep:** {reason}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Botun bu rolü alma yetkisi yok.",
            ephemeral=True
        )
    except discord.HTTPException as error:
        await interaction.response.send_message(
            f"❌ Rol alma sırasında Discord hatası oluştu: {error}",
            ephemeral=True
        )


# ==============================
# DUYURU
# ==============================

@bot.tree.command(
    name="duyuru",
    description="Bulunduğun kanala duyuru gönderir.",
    guild=GUILD
)
@app_commands.describe(
    message="Duyuru mesajı"
)
async def duyuru(
    interaction: discord.Interaction,
    message: str
):
    if not await check_permission(interaction):
        return

    if interaction.channel is None:
        await interaction.response.send_message(
            "❌ Duyuru kanalı bulunamadı.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📢 DUYURU",
        description=message,
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(
        text=f"Duyuran: {interaction.user}"
    )

    try:
        await interaction.channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ Duyuru gönderildi.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Botun bu kanala mesaj gönderme yetkisi yok.",
            ephemeral=True
        )
    except discord.HTTPException as error:
        await interaction.response.send_message(
            f"❌ Duyuru gönderilirken Discord hatası oluştu: {error}",
            ephemeral=True
        )


# ==============================
# ENGEL EKLE
# ==============================

@bot.tree.command(
    name="engel-ekle",
    description="Kullanıcıyı mesaj ve ses kanalından engeller.",
    guild=GUILD
)
@app_commands.describe(
    user_id="Engellenecek kullanıcının ID'si"
)
async def engel_ekle(
    interaction: discord.Interaction,
    user_id: str
):
    if not await check_permission(interaction):
        return

    try:
        user_id_int = int(user_id)
    except ValueError:
        await interaction.response.send_message(
            "❌ Geçerli bir kullanıcı ID'si gir.",
            ephemeral=True
        )
        return

    BLOCKED_USER_IDS.add(user_id_int)
    save_blocked_users()

    await interaction.response.send_message(
        f"🚫 `{user_id_int}` ID'li kullanıcı engellendi.\n"
        "Mesajları silinecek ve sese girerse sesten atılacak."
    )


# ==============================
# ENGEL KALDIR
# ==============================

@bot.tree.command(
    name="engel-kaldir",
    description="Kullanıcının mesaj ve ses kanalındaki engelini kaldırır.",
    guild=GUILD
)
@app_commands.describe(
    user_id="Engeli kaldırılacak kullanıcının ID'si"
)
async def engel_kaldir(
    interaction: discord.Interaction,
    user_id: str
):
    if not await check_permission(interaction):
        return

    try:
        user_id_int = int(user_id)
    except ValueError:
        await interaction.response.send_message(
            "❌ Geçerli bir kullanıcı ID'si gir.",
            ephemeral=True
        )
        return

    if user_id_int not in BLOCKED_USER_IDS:
        await interaction.response.send_message(
            f"ℹ️ `{user_id_int}` ID'li kullanıcı zaten engelli değil.",
            ephemeral=True
        )
        return

    BLOCKED_USER_IDS.remove(user_id_int)
    save_blocked_users()

    await interaction.response.send_message(
        f"✅ `{user_id_int}` ID'li kullanıcının engeli kaldırıldı."
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

            # ==========================
            # KANALLARI LİSTELE
            # ==========================

            if text.lower() == "channels":
                guild = bot.get_guild(GUILD_ID)

                if guild is None:
                    print("❌ Sunucu bulunamadı.")
                    continue

                print("")
                print("📢 SUNUCUDAKİ KANALLAR")
                print("================================")

                for channel in guild.channels:
                    print(
                        f"{channel.name}\n"
                        f"ID: {channel.id}\n"
                        f"Tür: {channel.type}"
                    )
                    print("--------------------------------")

                continue


            # ==========================
            # ROLLERİ LİSTELE
            # ==========================

            if text.lower() == "roles":
                guild = bot.get_guild(GUILD_ID)

                if guild is None:
                    print("❌ Sunucu bulunamadı.")
                    continue

                print("")
                print("🛡️ SUNUCUDAKİ ROLLER")
                print("================================")

                for role in reversed(guild.roles):
                    print(
                        f"{role.name}\n"
                        f"ID: {role.id}"
                    )
                    print("--------------------------------")

                continue


            # ==========================
            # KULLANICI ENGELLE
            # ==========================

            if text.lower().startswith("engel "):
                value = text[6:].strip()

                try:
                    user_id = int(value)
                except ValueError:
                    print("❌ Geçerli kullanıcı ID gir.")
                    continue

                BLOCKED_USER_IDS.add(user_id)
                save_blocked_users()
                print(
                    f"🚫 {user_id} engellendi. "
                    "Mesajları silinecek ve sese girerse sesten atılacak."
                )
                continue


            # ==========================
            # KULLANICI ENGELİNİ KALDIR
            # ==========================

            if text.lower().startswith("engel-kaldır ") or text.lower().startswith("engel-kaldir "):
                value = text.split(" ", 1)[1].strip()

                try:
                    user_id = int(value)
                except ValueError:
                    print("❌ Geçerli kullanıcı ID gir.")
                    continue

                if user_id in BLOCKED_USER_IDS:
                    BLOCKED_USER_IDS.remove(user_id)
                    save_blocked_users()
                    print(f"✅ {user_id} engeli kaldırıldı.")
                else:
                    print(f"ℹ️ {user_id} zaten engelli değil.")
                continue


            # ==========================
            # ENGELLİLERİ GÖSTER
            # ==========================

            if text.lower() == "engelliler":
                print("")
                print("🚫 ENGELLENEN KULLANICILAR")
                print("================================")

                if not BLOCKED_USER_IDS:
                    print("Engellenen kullanıcı yok.")
                else:
                    for user_id in sorted(BLOCKED_USER_IDS):
                        print(f"ID: {user_id}")

                print("")
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
                print("channels")
                print("→ Sunucudaki tüm kanalları ve ID'lerini listeler.")
                print("")
                print("roles")
                print("→ Sunucudaki tüm rolleri ve ID'lerini listeler.")
                print("")
                print("engel ID")
                print("→ Kullanıcıyı mesaj ve ses kanalından engeller.")
                print("")
                print("engel-kaldir ID")
                print("→ Kullanıcının engelini kaldırır.")
                print("")
                print("engelliler")
                print("→ Engellenen kullanıcıların ID'lerini gösterir.")
                print("")
                print("Discord komutları:")
                print("→ /rol-ver, /rol-al, /duyuru")
                print("→ /engel-ekle, /engel-kaldir")
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
