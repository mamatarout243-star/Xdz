import logging
import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------- CONFIGURATION ----------
# Token – already included (keep this file PRIVATE)
TOKEN = "8771499102:AAHa6ZBv-6keup7CEzuS50_vI4gA84QUUaM"

OWNER_ID = 8350971422
OWNER_NAME = "Piyushh"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- ROLE CONFIG ----------
ROLES = {
    "Shadow":   {"team": "shadow",  "emoji": "🔴", "desc": "Kill a town member every night. Stay hidden. Dominate."},
    "Guardian": {"team": "town",    "emoji": "🟢", "desc": "Find the Shadows. Vote them out. Protect the town."},
    "Healer":   {"team": "town",    "emoji": "💙", "desc": "Save one player from death each night. Choose wisely."},
    "Oracle":   {"team": "town",    "emoji": "🟡", "desc": "Peek into someone's soul each night. Reveal the truth."},
    "Fool":     {"team": "fool",    "emoji": "🃏", "desc": "Get yourself eliminated by vote. Trick everyone to win."},
    "Sentinel": {"team": "town",    "emoji": "🛡", "desc": "Guard a player from any attack tonight. Be the shield."},
    "Phantom":  {"team": "phantom", "emoji": "⚫", "desc": "A lone killer. Eliminate everyone to claim victory."},
}

PHASE_TIME = 20
MIN_PLAYERS = 3

NIGHT_TAUNTS = [
    "The village sleeps... but not everyone.",
    "Candles go out one by one...",
    "Shadows move silently through the dark...",
    "Someone is making their move right now...",
    "The night is hungry tonight...",
]

DAY_TAUNTS = [
    "The sun rises... but at what cost?",
    "Everyone is a suspect. Trust no one.",
    "The town square fills with accusations...",
    "Lies are being told right now. Can you tell?",
    "The tension is electric. Who's next?",
]

WIN_BANNERS = {
    "town":    "GUARDIANS TRIUMPH!\n Town Wins!",
    "shadow":  "DARKNESS PREVAILS!\n Shadows Win!",
    "phantom": "NONE SHALL SURVIVE!\n Phantom Wins!",
    "fool":    "THE JOKE IS ON YOU!\n Fool Wins!",
}

def assign_roles(num_players):
    if num_players == 3:
        roles = ["Shadow", "Guardian", "Guardian"]
    elif num_players == 4:
        roles = ["Shadow", "Guardian", "Guardian", "Healer"]
    elif num_players == 5:
        roles = ["Shadow", "Guardian", "Guardian", "Healer", "Oracle"]
    elif num_players == 6:
        roles = ["Shadow", "Shadow", "Guardian", "Guardian", "Healer", "Oracle"]
    elif num_players == 7:
        roles = ["Shadow", "Shadow", "Guardian", "Guardian", "Healer", "Oracle", "Fool"]
    elif num_players == 8:
        roles = ["Shadow", "Shadow", "Guardian", "Guardian", "Guardian", "Healer", "Oracle", "Sentinel"]
    else:
        roles = ["Shadow", "Shadow", "Phantom", "Guardian", "Guardian", "Guardian", "Healer", "Oracle", "Sentinel"]
        roles += ["Guardian"] * (num_players - 9)
    random.shuffle(roles)
    return roles

def new_game():
    return {
        "phase": "lobby",
        "players": {},
        "joined": [],
        "votes": {},
        "night_actions": {},
        "round": 0,
        "host": None,
        "lobby_message_id": None,
        "vote_message_id": None,
    }

games = {}

def get_alive(game):
    return [uid for uid, p in game["players"].items() if p["alive"]]

def player_list_text(game):
    lines = []
    for i, uid in enumerate(game["joined"], 1):
        p = game["players"][uid]
        crown = " 👑" if uid == game["host"] else ""
        lines.append(f"  {i}. {p['name']}{crown}")
    return "\n".join(lines) if lines else "  No players yet..."

def check_win(game):
    alive = get_alive(game)
    shadows = [u for u in alive if game["players"][u]["role"] == "Shadow"]
    phantom = [u for u in alive if game["players"][u]["role"] == "Phantom"]
    non_evil = [u for u in alive if game["players"][u]["role"] not in ("Shadow", "Phantom")]
    if not shadows and not phantom:
        return "town"
    if len(shadows) >= len(non_evil):
        return "shadow"
    if phantom and len(alive) <= 2:
        return "phantom"
    return None

def lobby_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️  J O I N  G A M E  ⚔️", callback_data="join")],
        [InlineKeyboardButton("🚀  S T A R T  G A M E  🚀", callback_data="startgame")],
    ])

def lobby_text(game):
    count = len(game["joined"])
    host_name = game["players"][game["host"]]["name"]
    bar = "🟩" * count + "⬛" * max(0, MIN_PLAYERS - count)
    status = "Ready to start!" if count >= MIN_PLAYERS else f"Need {MIN_PLAYERS - count} more player(s)..."
    return (
        f"🌑 SHADOW GAME — LOBBY\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 Host: {host_name}\n"
        f"👥 Players: {count}  {bar}\n"
        f"📊 Status: {status}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Roster:\n"
        f"{player_list_text(game)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Tap the button below to join!\n"
        f"Host taps Start when ready."
    )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🌑 SHADOW GAME\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Welcome, {user.first_name}!\n\n"
        f"You've just stepped into the most deadly social deduction game on Telegram.\n\n"
        f"Deceive. Deduce. Dominate.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 Shadows — Kill in the dark\n"
        f"🟢 Guardians — Fight for survival\n"
        f"💙 Healer — Cheat death itself\n"
        f"🟡 Oracle — See through every lie\n"
        f"🛡 Sentinel — The last line of defense\n"
        f"🃏 Fool — Win by losing\n"
        f"⚫ Phantom — The lone predator\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Commands:\n"
        f"/newgame — Open a game lobby\n"
        f"/endgame — Force end current game\n"
        f"/roles — View all roles\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Created & owned by {OWNER_NAME}\n"
        f"Add me to a group and type /newgame!"
    )

async def roles_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎭 ALL ROLES\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for role, info in ROLES.items():
        text += f"{info['emoji']} {role}\n{info['desc']}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\nRoles are assigned randomly. Only YOU know yours via DM!"
    await update.message.reply_text(text)

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if update.effective_chat.type == "private":
        await update.message.reply_text("Shadow Game must be played in a group chat!\nAdd me to a group and use /newgame there.")
        return
    if chat_id in games and games[chat_id]["phase"] != "ended":
        await update.message.reply_text("A game is already running! Use /endgame to stop it first.")
        return
    games[chat_id] = new_game()
    game = games[chat_id]
    game["host"] = user.id
    game["players"][user.id] = {"name": user.first_name, "role": None, "alive": True, "team_at_start": None}
    game["joined"].append(user.id)
    msg = await update.message.reply_text(lobby_text(game), reply_markup=lobby_keyboard())
    game["lobby_message_id"] = msg.message_id

async def endgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if chat_id not in games or games[chat_id]["phase"] == "ended":
        await update.message.reply_text("No active game to end.")
        return
    game = games[chat_id]
    if user.id != game["host"] and user.id != OWNER_ID:
        await update.message.reply_text("Only the host or owner can end the game!")
        return
    game["phase"] = "ended"
    await update.message.reply_text("🛑 Game forcefully ended.\nThe shadows retreat... for now.")

async def game_loop(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    game = games[chat_id]
    try:
        while game["phase"] not in ("ended", "lobby"):
            if game["phase"] == "running":
                await _start_game_internal(chat_id, context)
                await asyncio.sleep(5)
                await run_night(chat_id, context)
            elif game["phase"] == "night":
                await asyncio.sleep(PHASE_TIME)
                await resolve_night(chat_id, context)
            elif game["phase"] == "day":
                await asyncio.sleep(PHASE_TIME)
                await run_vote(chat_id, context)
            elif game["phase"] == "vote":
                await asyncio.sleep(PHASE_TIME)
                await resolve_vote(chat_id, context)
            else:
                break
    except Exception as e:
        logger.exception(f"Game loop error in chat {chat_id}")
        await context.bot.send_message(chat_id, f"⚠️ Game crashed: {e}\nUse /newgame to restart.")
        game["phase"] = "ended"

async def _start_game_internal(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    game = games[chat_id]
    role_list = assign_roles(len(game["joined"]))
    for i, uid in enumerate(game["joined"]):
        role = role_list[i]
        game["players"][uid]["role"] = role
        game["players"][uid]["team_at_start"] = ROLES[role]["team"]

    failed_dm = []
    for uid in game["joined"]:
        role = game["players"][uid]["role"]
        info = ROLES[role]
        extra = ""
        if role == "Shadow":
            partners = [game["players"][u]["name"] for u in game["joined"]
                        if game["players"][u]["role"] == "Shadow" and u != uid]
            if partners:
                extra = f"\n\nYour Shadow partner(s): {', '.join(partners)}"
        try:
            await ctx.bot.send_message(
                uid,
                f"🎭 YOUR SECRET ROLE\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{info['emoji']} {role}\n\n"
                f"{info['desc']}"
                f"{extra}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Keep this secret. Trust no one.\n"
                f"Good luck, {game['players'][uid]['name']}!"
            )
        except Exception:
            failed_dm.append(game["players"][uid]["name"])

    warn = f"\n\nCould not DM: {', '.join(failed_dm)} — please start the bot first!" if failed_dm else ""
    summary = "\n".join([f"  {'👑' if uid == game['host'] else '👤'} {game['players'][uid]['name']}" for uid in game["joined"]])
    await ctx.bot.send_message(
        chat_id,
        f"SHADOW GAME BEGINS!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{len(game['joined'])} players entered the darkness:\n{summary}\n\n"
        f"Secret roles sent via DM!\n"
        f"Phase timer: {PHASE_TIME}s each\n\n"
        f"The village falls asleep in 5 seconds...{warn}"
    )
    game["phase"] = "night"

async def run_night(chat_id, ctx):
    game = games[chat_id]
    if game["phase"] == "ended": return
    game["phase"] = "night"
    game["round"] += 1
    game["night_actions"] = {}
    alive = get_alive(game)
    taunt = random.choice(NIGHT_TAUNTS)

    await ctx.bot.send_message(
        chat_id,
        f"🌙 NIGHT {game['round']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{taunt}\n\n"
        f"Everyone close your eyes.\n"
        f"Special roles — check your DMs now!\n\n"
        f"⏱ {PHASE_TIME} seconds for night actions\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

    for uid in alive:
        role = game["players"][uid]["role"]
        targets = [u for u in alive if u != uid]

        if role == "Shadow":
            t_list = [u for u in targets if game["players"][u]["role"] != "Shadow"]
            if t_list:
                kb = [[InlineKeyboardButton(f"Kill {game['players'][t]['name']}", callback_data=f"shadow_kill:{t}")] for t in t_list]
                try:
                    await ctx.bot.send_message(uid, f"🔴 SHADOW — Night {game['round']}\nChoose your kill target:", reply_markup=InlineKeyboardMarkup(kb))
                except: pass

        elif role == "Healer":
            kb = [[InlineKeyboardButton(f"Save {game['players'][t]['name']}", callback_data=f"heal:{t}")] for t in alive]
            try:
                await ctx.bot.send_message(uid, f"💙 HEALER — Night {game['round']}\nWho do you save tonight?", reply_markup=InlineKeyboardMarkup(kb))
            except: pass

        elif role == "Oracle":
            kb = [[InlineKeyboardButton(f"Investigate {game['players'][t]['name']}", callback_data=f"oracle:{t}")] for t in targets]
            try:
                await ctx.bot.send_message(uid, f"🟡 ORACLE — Night {game['round']}\nWho do you investigate?", reply_markup=InlineKeyboardMarkup(kb))
            except: pass

        elif role == "Sentinel":
            kb = [[InlineKeyboardButton(f"Guard {game['players'][t]['name']}", callback_data=f"sentinel:{t}")] for t in targets]
            try:
                await ctx.bot.send_message(uid, f"🛡 SENTINEL — Night {game['round']}\nWho do you guard tonight?", reply_markup=InlineKeyboardMarkup(kb))
            except: pass

        elif role == "Phantom":
            kb = [[InlineKeyboardButton(f"Eliminate {game['players'][t]['name']}", callback_data=f"phantom_kill:{t}")] for t in targets]
            try:
                await ctx.bot.send_message(uid, f"⚫ PHANTOM — Night {game['round']}\nChoose your prey:", reply_markup=InlineKeyboardMarkup(kb))
            except: pass

async def resolve_night(chat_id, ctx):
    game = games[chat_id]
    if game["phase"] == "ended": return

    actions = game["night_actions"]
    protected = set()
    killed = set()

    if actions.get("heal"): protected.add(actions["heal"])
    if actions.get("sentinel"): protected.add(actions["sentinel"])
    if actions.get("shadow_kill") and actions["shadow_kill"] not in protected:
        killed.add(actions["shadow_kill"])
    if actions.get("phantom_kill") and actions["phantom_kill"] not in protected:
        killed.add(actions["phantom_kill"])

    lines = [f"☀️ DAWN — Night {game['round']} Results\n━━━━━━━━━━━━━━━━━━━━━\n"]

    if not killed:
        lines.append("No one died last night!\nThe protectors were watching...")
    else:
        for uid in killed:
            game["players"][uid]["alive"] = False
            role = game["players"][uid]["role"]
            lines.append(f"💀 {game['players'][uid]['name']} was eliminated!\n   They were {ROLES[role]['emoji']} {role}")
            if role == "Fool":
                game["phase"] = "ended"
                await ctx.bot.send_message(chat_id,
                    "\n".join(lines) + f"\n\n{WIN_BANNERS['fool']}\n\n"
                    f"{game['players'][uid]['name']} tricked everyone into eliminating them!\nPlay again? /newgame")
                return

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━")
    await ctx.bot.send_message(chat_id, "\n".join(lines))

    winner = check_win(game)
    if winner:
        await announce_winner(chat_id, ctx, winner)
        return

    game["phase"] = "day"

async def run_day(chat_id, ctx):
    game = games[chat_id]
    if game["phase"] == "ended": return
    game["phase"] = "day"
    alive = get_alive(game)
    taunt = random.choice(DAY_TAUNTS)
    alive_text = "\n".join([f"  🟢 {game['players'][uid]['name']}" for uid in alive])

    await ctx.bot.send_message(
        chat_id,
        f"☀️ DAY {game['round']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{taunt}\n\n"
        f"Survivors ({len(alive)}):\n{alive_text}\n\n"
        f"Discuss, argue, accuse!\n"
        f"⏱ {PHASE_TIME} seconds to talk\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )

async def run_vote(chat_id, ctx):
    game = games[chat_id]
    if game["phase"] == "ended": return

    game["phase"] = "vote"
    game["votes"] = {}
    alive = get_alive(game)
    kb = [[InlineKeyboardButton(f"Vote {game['players'][uid]['name']}", callback_data=f"vote:{uid}")] for uid in alive]
    msg = await ctx.bot.send_message(
        chat_id,
        f"🗳 VOTING PHASE\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Cast your vote!\nWho do you think is the Shadow?\n\n"
        f"⏱ {PHASE_TIME} seconds — choose wisely!\n"
        f"Majority rules. Ties save everyone.\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    game["vote_message_id"] = msg.message_id

async def resolve_vote(chat_id, ctx):
    game = games[chat_id]
    if game["phase"] == "ended": return

    if game["vote_message_id"]:
        try:
            await ctx.bot.edit_message_reply_markup(chat_id, game["vote_message_id"])
        except:
            pass

    vote_count = {}
    for target in game["votes"].values():
        vote_count[target] = vote_count.get(target, 0) + 1

    lines = ["📊 VOTE RESULTS\n━━━━━━━━━━━━━━━━━━━━━\n"]

    if vote_count:
        for uid, count in sorted(vote_count.items(), key=lambda x: -x[1]):
            bar = "🟥" * count + "⬜" * max(0, len(get_alive(game)) - count)
            lines.append(f"  {game['players'][uid]['name']} — {count} vote(s) {bar}")

    if not vote_count:
        lines.append("No votes cast! Nobody eliminated.")
        await ctx.bot.send_message(chat_id, "\n".join(lines))
    else:
        max_votes = max(vote_count.values())
        top = [uid for uid, c in vote_count.items() if c == max_votes]

        if len(top) > 1:
            lines.append("\nTIE! No elimination this round.\nThe Shadows breathe a sigh of relief...")
            await ctx.bot.send_message(chat_id, "\n".join(lines) + "\n━━━━━━━━━━━━━━━━━━━━━")
        else:
            eliminated = top[0]
            game["players"][eliminated]["alive"] = False
            role = game["players"][eliminated]["role"]
            lines.append(f"\n💀 {game['players'][eliminated]['name']} has been eliminated!\n   They were {ROLES[role]['emoji']} {role}")
            await ctx.bot.send_message(chat_id, "\n".join(lines) + "\n━━━━━━━━━━━━━━━━━━━━━")

            if role == "Fool":
                game["phase"] = "ended"
                await ctx.bot.send_message(chat_id,
                    f"{WIN_BANNERS['fool']}\n\n"
                    f"{game['players'][eliminated]['name']} played the whole town!\n"
                    f"Got voted out on purpose. Pure genius.\n\nPlay again? /newgame")
                return

    winner = check_win(game)
    if winner:
        await announce_winner(chat_id, ctx, winner)
        return

    game["phase"] = "night"

async def announce_winner(chat_id, ctx, winner):
    game = games[chat_id]
    game["phase"] = "ended"

    flavor = {
        "town": "The Shadows have been purged. Peace returns to the village.",
        "shadow": "The Shadows consumed the light. Darkness reigns supreme.",
        "phantom": "The Phantom eliminated every soul. None survived.",
    }.get(winner, "The game has ended.")

    reveal = "\n".join([
        f"  {'🟢' if game['players'][uid]['alive'] else '💀'} {game['players'][uid]['name']} — "
        f"{ROLES[game['players'][uid]['role']]['emoji']} {game['players'][uid]['role']}"
        for uid in game["joined"]
    ])

    await ctx.bot.send_message(
        chat_id,
        f"{WIN_BANNERS.get(winner, 'GAME OVER')}\n\n"
        f"{flavor}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Final Roles Revealed:\n"
        f"{reveal}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Game by {OWNER_NAME}\n"
        f"Play again? /newgame"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user = query.from_user

    if chat_id not in games:
        await query.answer("No active game!", show_alert=True)
        return

    game = games[chat_id]
    data = query.data

    if data.startswith(("shadow_kill:", "heal:", "oracle:", "sentinel:", "phantom_kill:", "vote:")):
        if not game["players"].get(user.id, {}).get("alive"):
            await query.answer("You are dead! 💀", show_alert=True)
            return

    if data == "join":
        if game["phase"] != "lobby":
            await query.answer("Game already started!", show_alert=True)
            return
        if user.id in game["players"]:
            await query.answer("You already joined!", show_alert=True)
            return
        game["players"][user.id] = {"name": user.first_name, "role": None, "alive": True, "team_at_start": None}
        game["joined"].append(user.id)
        await query.edit_message_text(lobby_text(game), reply_markup=lobby_keyboard())

    elif data == "startgame":
        if user.id != game["host"]:
            await query.answer("Only the host can start!", show_alert=True)
            return
        if len(game["joined"]) < MIN_PLAYERS:
            await query.answer(f"Need at least {MIN_PLAYERS} players!", show_alert=True)
            return
        await query.edit_message_text(
            "SHADOW GAME IS STARTING!\n\nCheck your DMs for your secret role!\nThe shadows are gathering..."
        )
        game["phase"] = "running"
        asyncio.create_task(game_loop(chat_id, context))

    elif data.startswith("shadow_kill:"):
        target_id = int(data.split(":")[1])
        if game["phase"] != "night":
            await query.answer("Not night phase!", show_alert=True)
            return
        if game["players"].get(user.id, {}).get("role") != "Shadow":
            await query.answer("You are not a Shadow!", show_alert=True)
            return
        game["night_actions"]["shadow_kill"] = target_id
        await query.edit_message_text(
            f"🔴 Shadow Action Locked\n\nTarget: {game['players'][target_id]['name']}\n\nWaiting for night to end..."
        )

    elif data.startswith("heal:"):
        target_id = int(data.split(":")[1])
        if game["phase"] != "night":
            await query.answer("Not night phase!", show_alert=True)
            return
        if game["players"].get(user.id, {}).get("role") != "Healer":
            await query.answer("You are not a Healer!", show_alert=True)
            return
        game["night_actions"]["heal"] = target_id
        await query.edit_message_text(
            f"💙 Healer Action Locked\n\nSaving: {game['players'][target_id]['name']}\n\nWaiting for night to end..."
        )

    elif data.startswith("oracle:"):
        target_id = int(data.split(":")[1])
        if game["phase"] != "night":
            await query.answer("Not night phase!", show_alert=True)
            return
        if game["players"].get(user.id, {}).get("role") != "Oracle":
            await query.answer("You are not an Oracle!", show_alert=True)
            return
        game["night_actions"]["oracle"] = target_id
        role = game["players"][target_id]["role"]
        team = ROLES[role]["team"]
        result = "EVIL — Shadow or Phantom!" if team in ("shadow", "phantom") else "INNOCENT — Town aligned."
        await query.edit_message_text(
            f"🟡 Oracle Vision\n\nYou investigated: {game['players'][target_id]['name']}\n\nResult: {result}\n\nUse this wisely."
        )

    elif data.startswith("sentinel:"):
        target_id = int(data.split(":")[1])
        if game["phase"] != "night":
            await query.answer("Not night phase!", show_alert=True)
            return
        if game["players"].get(user.id, {}).get("role") != "Sentinel":
            await query.answer("You are not a Sentinel!", show_alert=True)
            return
        game["night_actions"]["sentinel"] = target_id
        await query.edit_message_text(
            f"🛡 Sentinel Action Locked\n\nGuarding: {game['players'][target_id]['name']} tonight.\n\nNo one gets through you."
        )

    elif data.startswith("phantom_kill:"):
        target_id = int(data.split(":")[1])
        if game["phase"] != "night":
            await query.answer("Not night phase!", show_alert=True)
            return
        if game["players"].get(user.id, {}).get("role") != "Phantom":
            await query.answer("You are not the Phantom!", show_alert=True)
            return
        game["night_actions"]["phantom_kill"] = target_id
        await query.edit_message_text(
            f"⚫ Phantom Strike Locked\n\nEliminating: {game['players'][target_id]['name']}\n\nThey never saw it coming..."
        )

    elif data.startswith("vote:"):
        target_id = int(data.split(":")[1])
        if game["phase"] != "vote":
            await query.answer("Not voting phase!", show_alert=True)
            return
        if user.id == target_id:
            await query.answer("Can't vote for yourself!", show_alert=True)
            return
        game["votes"][user.id] = target_id
        await query.answer(f"Voted for {game['players'][target_id]['name']}!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("endgame", endgame))
    app.add_handler(CommandHandler("roles", roles_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info(f"Shadow Game Bot by {OWNER_NAME} is LIVE!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()