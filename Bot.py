# Bot.py
import os
import asyncio
import time
from aiohttp import web
from telebot.async_telebot import AsyncTeleBot
from telebot import types

import Database
import Models
import Errors

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = AsyncTeleBot(TOKEN)

group_awake_states = {}

LANGUAGES_ARRAY = [
    "Arabic", "Bahasa Indonesia", "Bahasa Melayu", "Bengali", "English", "French", 
    "German", "Gujarati", "Hindi", "Italian", "Kannada", "Malayalam", "Mandarin", 
    "Marathi", "Odia", "Persian", "Portuguese", "Punjabi", "Russian", "Sanskrit", 
    "Spanish", "Tamil", "Telugu", "Ukrainian", "Urdu", "Uzbek", "Vietnamese"
]

async def web_ping_handler(request):
    return web.Response(text="Hazel Engine is active and running 24/7!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", web_ping_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    Errors.logger.info(f"Web server successfully bound to port {port}")

async def check_admin(chat_id, user_id):
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception: return False

def update_activity(group_id, explicit_state=None):
    current_time = time.time()
    if group_id not in group_awake_states:
        group_awake_states[group_id] = {"status": "sleep", "last_event": current_time}
    if explicit_state:
        group_awake_states[group_id]["status"] = explicit_state
    group_awake_states[group_id]["last_event"] = current_time

def is_group_awake(group_id):
    if group_id not in group_awake_states: return False
    if group_awake_states[group_id]["status"] == "awake":
        if time.time() - group_awake_states[group_id]["last_event"] > 300:
            group_awake_states[group_id]["status"] = "sleep"
    return group_awake_states[group_id]["status"] == "awake"

async def delayed_message_deletion(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try: await bot.delete_message(chat_id, message_id)
    except Exception: pass

def generate_settings_keyboard(config):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🌐 Group Language: {config['language']}", callback_data="set_lang_nav"),
        types.InlineKeyboardButton(f"🔄 Translation: {'Enabled' if config['translation'] else 'Disabled'}", callback_data="toggle_translation"),
        types.InlineKeyboardButton(f"🎙️ AI Voice Chat: {'Enabled' if config['voice_chat'] else 'Disabled'}", callback_data="toggle_voice"),
        types.InlineKeyboardButton(f"🎭 Bot Tone: {config['tone']}", callback_data="cycle_tone")
    )
    return markup

@bot.message_handler(commands=['about_Hazel'])
async def about_hazel_command(message):
    if message.chat.type == "private": return
    try: await bot.delete_message(message.chat.id, message.message_id)
    except Exception: pass
    
    help_text = (
        "✨ *Hazel Multimodal System Guide* ✨\n\n"
        "💬 *Chat*: Mention 'Hi', 'Hello', or 'Hazel' to wake me up. Once awake, I only respond to messages replying directly to me.\n\n"
        "🎙️ `/aud2txt` — Reply to audio to transcribe it.\n"
        "🖼️ `/img2text` — Reply to an image to describe it, or ask a question.\n"
        "🎨 `/txt2img` — Reply to a text prompt to generate an image.\n"
        "🎵 `/txt2aud` — Reply to text to generate a voice message.\n"
        "🗣️ `/voice2voice` — Reply to a voice message to get an AI voice reply.\n"
        "🌐 `/tr` — Reply to text to translate it to English.\n"
        "⚙️ `/settings` — Admin configuration panel."
    )
    await bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['settings'])
async def settings_panel(message):
    if message.chat.type == "private": return
    try: await bot.delete_message(message.chat.id, message.message_id)
    except Exception: pass

    if not await check_admin(message.chat.id, message.from_user.id): return

    group_id = message.chat.id
    config = Database.get_group_config(group_id)
    markup = generate_settings_keyboard(config)
    panel_msg = await bot.send_message(group_id, "🔧 *Hazel Core Settings Dashboard*", reply_markup=markup, parse_mode="Markdown")
    asyncio.create_task(delayed_message_deletion(group_id, panel_msg.message_id, 180))

@bot.callback_query_handler(func=lambda call: True)
async def handle_callbacks(call):
    if not await check_admin(call.message.chat.id, call.from_user.id):
        await bot.answer_callback_query(call.id, "Clearance Required.", show_alert=True)
        return

    group_id = call.message.chat.id
    config = Database.get_group_config(group_id)

    if call.data == "toggle_translation":
        config['translation'] = not config['translation']
        Database.update_group_config(group_id, "translation", config['translation'])
        await bot.edit_message_reply_markup(group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config))
    elif call.data == "toggle_voice":
        config['voice_chat'] = not config['voice_chat']
        Database.update_group_config(group_id, "voice_chat", config['voice_chat'])
        await bot.edit_message_reply_markup(group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config))
    elif call.data == "cycle_tone":
        tones = ["Friendly", "Angry", "Funny", "Sad", "Mixed", "Situational"]
        config['tone'] = tones[(tones.index(config['tone']) + 1) % len(tones)]
        Database.update_group_config(group_id, "tone", config['tone'])
        await bot.edit_message_reply_markup(group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config))
    elif call.data == "set_lang_nav":
        lang_markup = types.InlineKeyboardMarkup(row_width=3)
        lang_markup.add(*[types.InlineKeyboardButton(lang, callback_data=f"sl_{lang}") for lang in LANGUAGES_ARRAY])
        await bot.edit_message_text("Select Group Target Language:", group_id, call.message.message_id, reply_markup=lang_markup)
    elif call.data.startswith("sl_"):
        config['language'] = call.data.split("_")[1]
        Database.update_group_config(group_id, "language", config['language'])
        await bot.edit_message_text("🔧 *Hazel Core Settings Dashboard*", group_id, call.message.message_id, reply_markup=generate_settings_keyboard(config), parse_mode="Markdown")
    await bot.answer_callback_query(call.id)

# INSTRUCTION ADDED: `/txt2aud` and `/voice2voice` routing commands
@bot.message_handler(commands=['aud2txt', 'img2text', 'txt2img', 'txt2aud', 'voice2voice', 'tr'])
async def process_targeted_commands(message):
    if message.chat.type == "private" or not message.reply_to_message: return
    cmd = message.text.split()[0].split('@')[0]
    target = message.reply_to_message
    chat_id = message.chat.id

    try: await bot.delete_message(chat_id, message.message_id)
    except Exception: pass

    config = Database.get_group_config(chat_id)
    status_msg = await bot.send_message(chat_id, "⏳ Analysing...", reply_to_message_id=target.message_id)

    try:
        if cmd == "/aud2txt" and (target.audio or target.voice):
            await bot.edit_message_text("🎙️ Transcribing wave segments...", chat_id, status_msg.message_id)
            file_info = await bot.get_file(target.voice.file_id if target.voice else target.audio.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            local_path = f"temp_{target.message_id}.ogg"
            with open(local_path, 'wb') as f: f.write(downloaded_file)
            text_output = await Models.speech_to_text_conversion(local_path)
            os.remove(local_path)
            await bot.edit_message_text(f"📝 *Transcription Complete*:\n\n{text_output}", chat_id, status_msg.message_id, parse_mode="Markdown")

        elif cmd == "/txt2aud" and target.text:
            await bot.edit_message_text("🎵 Converting text block into natural speech...", chat_id, status_msg.message_id)
            audio_bytes = await Models.text_to_speech_conversion(target.text)
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_voice(chat_id, audio_bytes, reply_to_message_id=target.message_id)
            
        elif cmd == "/voice2voice" and (target.audio or target.voice):
            if not config['voice_chat']:
                await bot.edit_message_text("⚠️ Voice conversational modules are disabled in group settings.", chat_id, status_msg.message_id)
                return
            await bot.edit_message_text("🗣️ Analyzing audio and synthesizing AI vocal response...", chat_id, status_msg.message_id)
            file_info = await bot.get_file(target.voice.file_id if target.voice else target.audio.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            local_path = f"temp_v2v_{target.message_id}.ogg"
            with open(local_path, 'wb') as f: f.write(downloaded_file)
            
            audio_bytes = await Models.voice_to_voice_conversion(local_path)
            os.remove(local_path)
            
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_voice(chat_id, audio_bytes, reply_to_message_id=target.message_id)

        elif cmd == "/img2text" and target.photo:
            await bot.edit_message_text("🔍 Processing image frames...", chat_id, status_msg.message_id)
            file_info = await bot.get_file(target.photo[-1].file_id)
            img_bytes = await bot.download_file(file_info.file_path)
            sub_prompt = message.text.replace(cmd, "").strip()
            desc = await Models.image_to_text_description(img_bytes, prompt=sub_prompt if sub_prompt else None)
            await bot.edit_message_text(f"🖼️ *Description*:\n\n{desc}", chat_id, status_msg.message_id, parse_mode="Markdown")

        elif cmd == "/tr" and target.text:
            if not config['translation']:
                await bot.edit_message_text("⚠️ Translation modules are disabled.", chat_id, status_msg.message_id)
                return
            await bot.edit_message_text("🌐 Re-mapping linguistic tokens to English...", chat_id, status_msg.message_id)
            translation = await Models.text_translation_to_english(target.text)
            await bot.edit_message_text(f"🇬🇧 *Translation*:\n\n{translation}", chat_id, status_msg.message_id, parse_mode="Markdown")

        elif cmd == "/txt2img" and target.text:
            await bot.edit_message_text("🎨 Rendering graphic pixels...", chat_id, status_msg.message_id)
            img_raw = await Models.text_to_image_generation(target.text)
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_photo(chat_id, img_raw, reply_to_message_id=target.message_id)
    except Exception as e:
        await bot.delete_message(chat_id, status_msg.message_id)
        await Errors.handle_error(bot, chat_id, e, f"Command {cmd} exception")

@bot.message_handler(func=lambda msg: msg.chat.type != "private")
async def handle_group_chat_flows(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""
    if not text: return

    # INSTRUCTION ADDED: Extract lowercase text for case-insensitive matching
    text_lower = text.lower()
    config = Database.get_group_config(chat_id)

    if text_lower in ["stop", "turn off", "shut up"]:
        if is_group_awake(chat_id) and message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id:
            update_activity(chat_id, explicit_state="sleep")
            await bot.send_message(chat_id, "Ok ! Im going to Sleep 🥱", reply_to_message_id=message.message_id)
            return

    if text_lower in ["hi", "hello", "hazel"]:
        update_activity(chat_id, explicit_state="awake")
        await bot.send_message(chat_id, "Hi😊", reply_to_message_id=message.message_id)
        return

    if message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id:
        if not is_group_awake(chat_id): update_activity(chat_id, explicit_state="awake")
        update_activity(chat_id)
        
        status_msg = await bot.send_message(chat_id, "💭 Processing context...", reply_to_message_id=message.message_id)
        try:
            reply = await Models.text_to_text_generation(text, language=config['language'], tone=config['tone'])
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_message(chat_id, reply, reply_to_message_id=message.message_id)
        except Exception as e:
            await bot.delete_message(chat_id, status_msg.message_id)
            await Errors.handle_error(bot, chat_id, e, "Text engine failure")

async def main():
    Database.init_db()
    await start_web_server()
    Errors.logger.info("Hazel Web Service engine active. Starting long-polling thread...")
    await bot.polling(non_stop=True)

if __name__ == "__main__":
    asyncio.run(main())
