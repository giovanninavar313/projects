import os
import asyncio
import datetime as dt
from typing import Optional, List

import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from dotenv import load_dotenv

# ------------------- CONFIG -------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "MTQxMzQ0MDA4MzY5MTk2MjQ3MA.GElw3I.N2ecSxysNvzYuxNv9GkVtH20uUqZ01Fm6Ycqi4")
GUILD_ID = int(os.getenv("GUILD_ID", "1413442425288003636"))  
STAFF_ROLE_NAME = os.getenv("STAFF_ROLE", "Dipendente")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1413442868088934523"))
PRENOTAZIONI_CHANNEL_ID = int(os.getenv("PRENOTAZIONI_CHANNEL_ID", "1413443076701028434"))

INTENTS = discord.Intents.default()
INTENTS.members = True  # per DM / resolve users

DB_PATH = "gabrix_bot.db"

# ------------------- BOT CON SETUP_HOOK -------------------
class GabrixBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)
        self.synced_guild: Optional[discord.Object] = (
            discord.Object(id=GUILD_ID) if GUILD_ID else None
        )

    async def setup_hook(self) -> None:
        # DB pronto prima di syncare comandi
        await init_db()

        # Se hai GUILD_ID, copio i global nella guild e li sync-o subito (visibili in pochi secondi)
        try:
            if self.synced_guild:
                self.tree.copy_global_to(guild=self.synced_guild)
                synced = await self.tree.sync(guild=self.synced_guild)
                print(f"✅ Synced {len(synced)} guild commands in {self.synced_guild.id}")
            else:
                synced = await self.tree.sync()
                print(f"✅ Synced {len(synced)} global commands")
        except Exception as e:
            print("❌ Sync error:", e)

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")


bot = GabrixBot()
tree = bot.tree

# ------------------- UTILS / DB -------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS shifts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                nome TEXT,
                start_time TEXT,
                end_time TEXT,
                start_proof_url TEXT,
                end_proof_url TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sales(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                prodotto TEXT,
                prezzo REAL,
                venduto_da TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS reviews(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                nome TEXT,
                stelle INTEGER,
                note TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS bookings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                persone INTEGER,
                giorno TEXT,
                ora TEXT,
                created_at TEXT,
                status TEXT
            );
            """
        )
        await db.commit()

def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Comando disponibile solo nel server.", ephemeral=True)
            return False
        has_role = any(r.name == STAFF_ROLE_NAME for r in interaction.user.roles)
        if not has_role:
            await interaction.response.send_message(f"Serve il ruolo **{STAFF_ROLE_NAME}**.", ephemeral=True)
        return has_role
    return app_commands.check(predicate)

def log_channel(guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
    if not guild or LOG_CHANNEL_ID == 0:
        return None
    ch = guild.get_channel(LOG_CHANNEL_ID)
    return ch if isinstance(ch, discord.TextChannel) else None

def prenotazioni_channel(guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
    if not guild or PRENOTAZIONI_CHANNEL_ID == 0:
        return None
    ch = guild.get_channel(PRENOTAZIONI_CHANNEL_ID)
    return ch if isinstance(ch, discord.TextChannel) else None

# ------------------- DIAGNOSTICA / TEST -------------------
@tree.command(name="ping", description="Test rapido (se vedi questo, gli slash funzionano).")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🏓", ephemeral=True)

@tree.command(name="debug_sync", description="Mostra info sync comandi (solo Staff).")
@is_staff()
async def debug_sync(interaction: discord.Interaction):
    guild = interaction.guild
    if bot.synced_guild:
        cmds = await tree.fetch_commands(guild=bot.synced_guild)
        await interaction.response.send_message(
            f"Guild ID: {bot.synced_guild.id}\nComandi registrati in guild: {len(cmds)}", ephemeral=True
        )
    else:
        cmds = await tree.fetch_commands()
        await interaction.response.send_message(
            f"Comandi globali registrati: {len(cmds)} (possono impiegare fino a 60 min per comparire).",
            ephemeral=True
        )

# ------------------- DIPENDENTI -------------------
@tree.command(name="invia_turno", description="Invia il turno di lavoro.")
@is_staff()
@app_commands.describe(
    nome="Il tuo nome (o quello del dipendente)",
    inizio="Ora di inizio turno (es. 18:00)",
    fine="Ora di fine turno (es. 23:30)",
    prova_inizio="Prova d'inizio turno (screenshot/foto)",
    prova_fine="Prova di fine turno (screenshot/foto)"
)
async def invia_turno(
    interaction: discord.Interaction,
    nome: str,
    inizio: str,
    fine: str,
    prova_inizio: Optional[discord.Attachment] = None,
    prova_fine: Optional[discord.Attachment] = None,
):
    await interaction.response.defer(ephemeral=True, thinking=True)
    now = dt.datetime.utcnow().isoformat()
    start_url = prova_inizio.url if prova_inizio else ""
    end_url = prova_fine.url if prova_fine else ""

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shifts (user_id,user_name,nome,start_time,end_time,start_proof_url,end_proof_url,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (interaction.user.id, str(interaction.user), nome, inizio, fine, start_url, end_url, now),
        )
        await db.commit()

    emb = discord.Embed(title="Turno inviato", color=0x2ecc71)
    emb.add_field(name="Nome", value=discord.utils.escape_markdown(nome), inline=True)
    emb.add_field(name="Inizio", value=inizio, inline=True)
    emb.add_field(name="Fine", value=fine, inline=True)
    if start_url: emb.add_field(name="Prova inizio", value=f"[Apri]({start_url})", inline=False)
    if end_url: emb.add_field(name="Prova fine", value=f"[Apri]({end_url})", inline=False)
    emb.set_footer(text=f"Da: {interaction.user}")

    await interaction.followup.send("✅ Turno registrato.", ephemeral=True)
    ch = log_channel(interaction.guild)
    if ch: await ch.send(embed=emb)

@tree.command(name="registra_vendita", description="Registra una vendita.")
@is_staff()
@app_commands.describe(
    prodotto="Nome prodotto",
    prezzo="Prezzo (es. 8.50)",
    venduto_da="Chi ha effettuato la vendita (se diverso da chi invia)"
)
async def registra_vendita(
    interaction: discord.Interaction,
    prodotto: str,
    prezzo: app_commands.Range[float, 0, 1000],
    venduto_da: Optional[str] = None,
):
    await interaction.response.defer(ephemeral=True, thinking=True)
    venditore = venduto_da or interaction.user.display_name
    now = dt.datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sales (user_id,user_name,prodotto,prezzo,venduto_da,created_at) VALUES (?,?,?,?,?,?)",
            (interaction.user.id, str(interaction.user), prodotto, float(prezzo), venditore, now),
        )
        await db.commit()

    emb = discord.Embed(title="Nuova vendita", color=0xf1c40f)
    emb.add_field(name="Prodotto", value=discord.utils.escape_markdown(prodotto), inline=True)
    emb.add_field(name="Prezzo", value=f"€ {float(prezzo):.2f}", inline=True)
    emb.add_field(name="Venduto da", value=venditore, inline=True)
    emb.set_footer(text=f"Registrata da: {interaction.user}")

    await interaction.followup.send("✅ Vendita registrata.", ephemeral=True)
    ch = log_channel(interaction.guild)
    if ch: await ch.send(embed=emb)

@tree.command(name="apri", description="Invia un messaggio di apertura con ping @here.")
@is_staff()
async def apri(interaction: discord.Interaction):
    await interaction.response.send_message(
        content="@here 🔔 **Apertura locale!** Siamo operativi — prenota su Discord!",
        allowed_mentions=discord.AllowedMentions(everyone=True)
    )

@tree.command(name="chiudi", description="Invia un messaggio di chiusura.")
@is_staff()
async def chiudi(interaction: discord.Interaction):
    await interaction.response.send_message("🔕 **Chiusura locale** — grazie a tutti e a domani!")

@tree.command(name="accetta_prenotazione", description="Invia un DM di prenotazione accettata.")
@is_staff()
@app_commands.describe(utente="Utente da avvisare")
async def accetta_prenotazione(interaction: discord.Interaction, utente: discord.User):
    try:
        await utente.send("✅ La tua prenotazione alla **Pizzeria da Gabrix** è stata *accettata*. Ti aspettiamo! 🍕")
        await interaction.response.send_message(f"Messaggio inviato a {utente.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Impossibile inviare DM: utente con DM chiusi.", ephemeral=True)

@tree.command(name="rifiuta_prenotazione", description="Invia un DM di prenotazione rifiutata.")
@is_staff()
@app_commands.describe(utente="Utente da avvisare", motivo="Motivo (opzionale)")
async def rifiuta_prenotazione(interaction: discord.Interaction, utente: discord.User, motivo: Optional[str] = None):
    try:
        msg = "❌ La tua prenotazione alla **Pizzeria da Gabrix** è stata *rifiutata*."
        if motivo: msg += f"\nMotivo: {motivo}"
        msg += "\nScrivici su Discord per riprogrammare!"
        await utente.send(msg)
        await interaction.response.send_message(f"Messaggio inviato a {utente.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Impossibile inviare DM: utente con DM chiusi.", ephemeral=True)

# ------------------- CITTADINI -------------------
@tree.command(name="recensione", description="Lascia una recensione.")
@app_commands.describe(
    nome="Il tuo nome (o nickname)",
    stelle="Valutazione 1–5",
    note="Note opzionali (max 300 caratteri)"
)
async def recensione(
    interaction: discord.Interaction,
    nome: str,
    stelle: app_commands.Range[int, 1, 5],
    note: Optional[str] = None
):
    await interaction.response.defer(ephemeral=True, thinking=True)
    now = dt.datetime.utcnow().isoformat()
    note = (note or "")[:300]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reviews (user_id,user_name,nome,stelle,note,created_at) VALUES (?,?,?,?,?,?)",
            (interaction.user.id, str(interaction.user), nome, int(stelle), note, now),
        )
        await db.commit()

    stars = "★" * int(stelle) + "☆" * (5 - int(stelle))
    emb = discord.Embed(title="Nuova recensione", color=0xe74c3c)
    emb.add_field(name="Nome", value=discord.utils.escape_markdown(nome), inline=True)
    emb.add_field(name="Stelle", value=f"{stars} ({int(stelle)}/5)", inline=True)
    if note: emb.add_field(name="Note", value=note, inline=False)

    await interaction.followup.send("Grazie per la tua recensione! ❤️", ephemeral=True)
    ch = log_channel(interaction.guild)
    if ch: await ch.send(embed=emb)

@tree.command(name="prenota", description="Prenota un tavolo.")
@app_commands.describe(
    persone="Numero di persone",
    giorno="Giorno (AAAA-MM-GG)",
    ora="Orario (HH:MM)"
)
async def prenota(
    interaction: discord.Interaction,
    persone: app_commands.Range[int, 1, 20],
    giorno: str,
    ora: str,
):
    # Validazioni base
    try:
        _ = dt.datetime.strptime(giorno, "%Y-%m-%d")
    except ValueError:
        await interaction.response.send_message("❌ Giorno non valido. Usa AAAA-MM-GG.", ephemeral=True)
        return
    if ":" not in ora:
        await interaction.response.send_message("❌ Orario non valido. Usa HH:MM.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    now = dt.datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bookings (user_id,user_name,persone,giorno,ora,created_at,status) VALUES (?,?,?,?,?,?,?)",
            (interaction.user.id, str(interaction.user), int(persone), giorno, ora, now, "pending"),
        )
        await db.commit()

    await interaction.followup.send(
        f"📩 Prenotazione ricevuta! {persone} persone il **{giorno}** alle **{ora}**. Ti contatteremo in DM.",
        ephemeral=True
    )

    ch = prenotazioni_channel(interaction.guild) or log_channel(interaction.guild)
    if ch:
        emb = discord.Embed(title="Nuova prenotazione", color=0x3498db)
        emb.add_field(name="Utente", value=interaction.user.mention, inline=True)
        emb.add_field(name="Persone", value=str(persone), inline=True)
        emb.add_field(name="Giorno", value=giorno, inline=True)
        emb.add_field(name="Ora", value=ora, inline=True)
        await ch.send(embed=emb)

# ------------------- RUN -------------------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ DISCORD_TOKEN non impostato (usa .env).")
    bot.run(TOKEN, log_handler=None)
