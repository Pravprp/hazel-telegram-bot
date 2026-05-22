# Errors.py
import logging

# Configure local logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HazelBot")

# ==========================================
# GLOBAL ERROR TOGGLE BUTTON
# True: Print failures inside the Telegram Group
# False: Absolute silence during failure/limit hits
# ==========================================
SHOW_ERRORS_IN_GROUP = True

async def handle_error(bot, chat_id, exception, context_msg="Processing failed"):
    """
    Logs errors internally and conditionally displays them inside the chat.
    """
    error_str = f"❌ [Hazel Error] {context_msg}: {str(exception)}"
    logger.error(error_str)
    
    if SHOW_ERRORS_IN_GROUP:
        try:
            await bot.send_message(chat_id, error_str)
        except Exception as e:
            logger.error(f"Failed to transmit error message over Telegram: {e}")