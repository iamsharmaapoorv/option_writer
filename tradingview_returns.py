import json
import logging
import re

import requests
from logging_utils import setup_logging
from telegram_alert import TelegramAlert


TRADINGVIEW_SYMBOLS = [
    ("ES1", "https://www.tradingview.com/symbols/CME_MINI-ES1!/"),
    ("NQ1", "https://www.tradingview.com/symbols/CME_MINI-NQ1!/"),
    ("NIFTY1", "https://www.tradingview.com/symbols/NSEIX-NIFTY1!/"),
]

USER_AGENT = {"User-Agent": "Mozilla/5.0"}


setup_logging("tradingview_returns")


def _extract_symbol_change(page_html: str):
    match = re.search(r'"symbol_screener_data":(\{.*?\}),"nearest_futures_contracts"', page_html, re.S)
    if not match:
        return None

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        logging.warning("Could not decode TradingView symbol_screener_data payload.")
        return None

    return payload.get("change")


def get_tradingview_returns_summary() -> str:
    parts = []

    for label, url in TRADINGVIEW_SYMBOLS:
        try:
            response = requests.get(url, headers=USER_AGENT, timeout=15)
            response.raise_for_status()
            change = _extract_symbol_change(response.text)
        except Exception as error:
            logging.warning(f"Failed to fetch TradingView return for {label}: {error}")
            change = None

        if change is None:
            parts.append(f"{label} N/A")
            continue

        parts.append(f"{label} {change:+.2f}%")

    return " | ".join(parts)


def send_tradingview_returns():
    message = get_tradingview_returns_summary()
    if not message:
        logging.info("No TradingView returns summary generated.")
        return

    TelegramAlert().send(message)


if __name__ == "__main__":
    send_tradingview_returns()
