#! usr/bin/env python3
import os
import logging
import requests


# ===== LOGGER SETUP =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("telegram.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ===== ALERT BASE CLASS =====
class AlertBase:
    def send(self, message):
        raise NotImplementedError


# ===== TELEGRAM ALERT =====
class TelegramAlert(AlertBase):
    def __init__(self, bot_token = None, chat_id = None):
        self.bot_token = bot_token if bot_token else os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id if chat_id else os.getenv("TELEGRAM_CHAT_ID")

    def send(self, message):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, data=payload)
            if res.status_code != 200:
                logger.error(f"Alert failed: {res.text}")
            else:
                logger.debug(f"Alert sent successfully to chat_id: {self.chat_id}")
        except Exception as e:
            logger.error(f"Alert error: {e}")


