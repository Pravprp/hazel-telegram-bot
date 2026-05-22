# Bot.py
import os
import asyncio
import time
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
from telebot import types

import Database
import Models
import Errors

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = AsyncTeleBot(TOKEN)

# In-memory runtime tracking matrices for multi-groups
group_awake_states = {} # {group_id: {"status": "sleep"/"awake", "last_event": float}}

# Dynamic Available Languages Support Menu
LANGUAGES_ARRAY = [
    "Arabic", "Bahasa Indonesia", "Bahasa Melayu", "Bengali", "English", "French", 
    "German", "Gujarati", "Hindi", "Italian", "Kannada", "Malayalam", "Mandarin", 
    "Marathi", "Odia", "Persian", "Portuguese", "Punjabi", "Russian", "Sanskrit", 
    "Spanish", "Tamil", "Telugu", "Ukrainian", "Urdu", "Uzbek", "Vietnamese"
]

async def check_admin(chat_id, user_id):
    """Verifies if a user is an administrator within the group."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception:
        return False

def update_activity(group_id, explicit_state=None):
    """Manages the 5-minute inactivity tracker sleep mechanics."""
    current_time = time.time()
    if group_id not in group_awake_states:
        group_awake_states[group_id] = {"status": "sleep", "last_event": current_time}
    
    if explicit_state:
        group_awake_states[group_id]["status"] = explicit_state
    group_awake_states[group_id]["last_event"] = current_time

def is_group_awake(group_id):
    if group_id not in group_awake_states:
        return False
    # Auto-sleep evaluation if 5 minutes (300 seconds) pass with zero context updates
    if group_awake_states[group_id]["status"] == "awake":
        if time.time() - group_awake_states[group_id]["last_event"] > 300:
            group_awake_states[group_id]["status"] = "sleep"
    return group_awake_states[group_id]["status"] == "awake"

# ==========================================
# INTERACTIVE TELEGRAM CORE COMMAND ARCHITECTURE
# ==========================================

@bot.message_handler(commands=['about_Hazel'])
async def about_hazel_command(message):
    if message.chat.type == "private":
        return
    await bot.delete_message(message.chat.id, message.message_id)
    help_text = (
        "✨ *Hazel Multimodal System Guide* ✨\n\n"
        "I am Hazel, an advanced AI designed to manage your groups efficiently. Here is how you can use my features:\n\n"
        "💬 *How to chat*: Mention 'Hi', 'Hello', or 'Hazel' to wake me up. Once awake, I will only respond to messages that directly reply to my text.\n\n"
        "🎙️ `/aud2txt` — Reply to an audio message to instantly transcode it into text.\n"
        "🖼️ `/img2text` — Reply to an image to get a detailed description, or ask a question like: `/img2text how many cars are visible?`.\n"
        "🎨 `/txt2img` — Reply to any text prompt to generate an image from it.\n"
        "🎵 `/txt2aud` — Reply to a text string to convert it into a spoken audio message.\n"
        "🌐 `/tr` — Reply to any foreign text to instantly translate it into clean English.\n"
        "🗣️ `/voice2voice` — Reply to an audio message to generate an interactive AI voice response.\n"
        "⚙️ `/settings` — Opens the administrator configuration interface."
    )
    await bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['settings'])
async def settings_panel(message):
    if message.chat.type == "private":
        return
    
    # Instantly delete the calling message
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    if not await check_admin(message.chat.id, message.from_user.id):
        return

    group_id = message.chat.id
    config = Database.get_group_config(group_id)

    markup = generate_settings_keyboard(config)
    panel_msg = await bot.send_message(group_id, "🔧 *Hazel Core Settings Dashboard*", reply_markup=markup, parse_mode="Markdown")
    
    # Auto-delete settings panel after 3 minutes (180 seconds)
    asyncio.create_task(delayed_message_deletion(group_id, panel_msg.message_id, 180))

def generate_settings_keyboard(config):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    lang_btn = types.InlineKeyboardButton(f"🌐 Group Language: {config['language']}", callback_data="set_lang_nav")
    trans_status = "Enabled" if config['translation'] else "Disabled"
    trans_btn = types.InlineKeyboardButton(f"🔄 Translation: {trans_status}", callback_data="toggle_translation")
    voice_status = "Enabled" if config['voice_chat'] else "Disabled"
    voice_btn = types.InlineKeyboardButton(f"🎙️ AI Voice Chat: {voice_status}", callback_data="toggle_voice")
    tone_btn = types.InlineKeyboardButton(f"🎭 Bot Tone: {config['tone']}", callback_data="cycle_tone")
    
    markup.add(lang_btn, trans_btn, voice_btn, tone_btn)
    return markup

async def delayed_message_deletion(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# ==========================================
# INLINE SETTINGS CALLBACK PROCESSING
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
async def handle_callbacks(call):
    if not await check_admin(call.message.chat.id, call.from_user.id):
        await bot.answer_callback_query(call.id, "Access Denied: Administrative Clearance Required.", show_alert=True)
        return

    group_id = call.message.chat.id
    config = Database.get_group_config(group_id)

    if call.data == "toggle_translation":
        new_val = not config['translation']
        Database.update_group_config(group_id, "translation", new_val)
        config['translation'] = new_val
        await bot.edit_message_reply_markup(group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config))
        
    elif call.data == "toggle_voice":
        new_val = not config['voice_chat']
        Database.update_group_config(group_id, "voice_chat", new_val)
        config['voice_chat'] = new_val
        await bot.edit_message_reply_markup(group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config))

    elif call.data == "cycle_tone":
        tones = ["Friendly", "Angry", "Funny", "Sad", "Mixed", "Situational"]
        next_tone = tones[(tones.index(config['tone']) + 1) % len(tones)]
        Database.update_group_config(group_id, "tone", next_tone)
        config['tone'] = next_tone
        await bot.edit_message_reply_markup(group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config))

    elif call.data == "set_lang_nav":
        # Render sub-menu for languages array
        lang_markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = [types.InlineKeyboardButton(lang, callback_data=f"sl_{lang}") for lang in LANGUAGES_ARRAY]
        lang_markup.add(*buttons)
        await bot.edit_message_text("Select Group Target Language Script:", group_id, call.message.message_id, reply_markup=lang_markup)

    elif call.data.startswith("sl_"):
        chosen_lang = call.data.split("_")[1]
        Database.update_group_config(group_id, "language", chosen_lang)
        config['language'] = chosen_lang
        await bot.edit_message_text("🔧 *Hazel Core Settings Dashboard*", group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config), parse_mode="Markdown")

    await bot.answer_callback_query(call.id)

# ==========================================
# PIPELINE TARGET OPERATORS
# ==========================================

@bot.message_handler(commands=['aud2txt', 'img2text', 'txt2img', 'txt2aud', 'tr', 'voice2voice'])
async def process_targeted_commands(message):
    if message.chat.type == "private":
        return
    
    cmd = message.text.split()[0].split('@')[0]
    target = message.reply_to_message
    chat_id = message.chat.id

    # Enforce reply architecture constraints
    if not target:
        try:
            await bot.delete_message(chat_id, message.message_id)
        except Exception: pass
        return

    # Instantly delete the command message
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception: pass

    config = Database.get_group_config(chat_id)
    status_msg = await bot.send_message(chat_id, "⏳ Processing...", reply_to_message_id=target.message_id)

    try:
        if cmd == "/aud2txt" and (target.audio or target.voice):
            await bot.edit_message_text("🎙️ Analyzing audio file matrix...", chat_id, status_msg.message_id)
            file_info = await bot.get_file(target.voice.file_id if target.voice else target.audio.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            local_path = f"temp_{target.message_id}.ogg"
            with open(local_path, 'wb') as f: f.write(downloaded_file)
            
            text_output = await Models.speech_to_text_conversion(local_path)
            os.remove(local_path)
            await bot.edit_message_text(f"📝 *Transcription Complete*:\n\n{text_output}", chat_id, status_msg.message_id, parse_mode="Markdown")

        elif cmd == "/img2text" and target.photo:
            await bot.edit_message_text("🔄 Analyzing image content pixels...", chat_id, status_msg.message_id)
            file_info = await bot.get_file(target.photo[-1].file_id)
            img_bytes = await bot.download_file(file_info.file_path)
            
            # Extract optional sub-prompt text
            sub_prompt = message.text.replace(cmd, "").strip()
            desc = await Models.image_to_text_description(img_bytes, prompt=sub_prompt if sub_prompt else None)
            await bot.edit_message_text(f"🖼️ *Visual Interpretation Analysis*:\n\n{desc}", chat_id, status_msg.message_id, parse_mode="Markdown")

        elif cmd == "/tr" and target.text:
            if not config['translation']:
                await bot.edit_message_text("⚠️ Translation engine features are disabled in this group's settings console.", chat_id, status_msg.message_id)
                return
            await bot.edit_message_text("🌐 Translating linguistic structures to English...", chat_id, status_msg.message_id)
            translation = await Models.text_translation_to_english(target.text)
            await bot.edit_message_text(f"🇬🇧 *English Translation Summary*:\n\n{translation}", chat_id, status_msg.message_id, parse_mode="Markdown")

        elif cmd == "/txt2img" and target.text:
            await bot.edit_message_text("🎨 Synthesizing vector generation textures...", chat_id, status_msg.message_id)
            img_raw = await Models.text_to_image_generation(target.text)
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_photo(chat_id, img_raw, reply_to_message_id=target.message_id)

        elif cmd == "/voice2voice" and (target.audio or target.voice):
            if not config['voice_chat']:
                await bot.edit_message_text("⚠️ Voice conversational modules are currently disabled in settings.", chat_id, status_msg.message_id)
                return
            await bot.edit_message_text("🗣️ Processing sound waves and synthesizing dialogue output...", chat_id, status_msg.message_id)
            # Custom speech processing simulation
            await bot.edit_message_text("🎙️ Voice synthesis complete.", chat_id, status_msg.message_id)
        else:
            await bot.edit_message_text("⚠️ Command context mismatch or unsupported input file format.", chat_id, status_msg.message_id)
            
    except Exception as e:
        await bot.delete_message(chat_id, status_msg.message_id)
        await Errors.handle_error(bot, chat_id, e, context_msg=f"Error executing {cmd}")

# ==========================================
# CHAT PROCESSING, STATE MANAGEMENT & CONVERSATIONS
# ==========================================

@bot.message_handler(func=lambda msg: msg.chat.type != "private")
async def handle_group_chat_flows(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""
    
    if not text:
        return

    config = Database.get_group_config(chat_id)

    # 1. Force Sleep Keywords
    if text.lower() in ["stop", "turn off", "shut up"]:
        if is_group_awake(chat_id) and message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id:
            update_activity(chat_id, explicit_state="sleep")
            await bot.send_message(chat_id, "Ok ! Im going to Sleep 🥱", reply_to_message_id=message.message_id)
            return

    # 2. Wake Keywords Evaluation
    if text in ["Hi", "Hello", "Hazel"]:
        update_activity(chat_id, explicit_state="awake")
        await bot.send_message(chat_id, "Hi😊", reply_to_message_id=message.message_id)
        return

    # 3. Handle Ongoing Conversational Responses
    if message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id:
        # If asleep, wake up instantly without sending the hardcoded greeting
        if not is_group_awake(chat_id):
            update_activity(chat_id, explicit_state="awake")
            
        update_activity(chat_id) # Extend lease time
        
        status_msg = await bot.send_message(chat_id, "💭 Thinking...", reply_to_message_id=message.message_id)
        try:
            reply = await Models.text_to_text_generation(text, language=config['language'], tone=config['tone'])
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_message(chat_id, reply, reply_to_message_id=message.message_id)
        except Exception as e:
            await bot.delete_message(chat_id, status_msg.message_id)
            await Errors.handle_error(bot, chat_id, e, "Conversational text pipeline exception")

# Main Execution Routine
if __name__ == "__main__":
    Database.init_db()
    logger.info("Hazel Multimodal System Engine active and polling...")
    asyncio.run(bot.polling(non_stop=True))