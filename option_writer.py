import requests
from bs4 import BeautifulSoup
import json
import logging
from bisect import bisect_left
from telegram_alert import TelegramAlert, AlertBase


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
)

ALERT_BUFFER = []


def flush_alert_buffer_global(alert_manager: AlertBase, alert_buffer: list, max_len: int = 3900):
    """Send alerts in batches up to `max_len` characters."""
    if not alert_buffer:
        logging.info("ℹ️ No alerts to send.")
        return

    current_batch = []
    current_len = 0

    for msg in alert_buffer:

        msg_len = len(msg)
        if current_len + msg_len > max_len:
            alert_manager.send("\n\n".join(current_batch))
            current_batch = [msg]
            current_len = msg_len
        else:
            current_batch.append(msg)
            current_len += msg_len

    if current_batch:
        alert_manager.send("\n\n".join(current_batch))

    alert_buffer.clear()


class OptionChainScraper:
    """Scrapes Groww option chain and evaluates premiums."""

    BASE_URL = "https://groww.in/options/"

    def __init__(
        self,
        stock_id: str,
        alert_manager: AlertBase,
        premium_lot_size: int = None,
        min_premium: int = 4000,
        min_oi: int = 50,
        use_global_buffer=False,
    ):
        self.stock_id = stock_id
        self.min_premium = min_premium if min_premium else 4000
        self.alert_manager = alert_manager
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.min_oi = min_oi
        self.premium_lot_size = premium_lot_size
        self.use_global_buffer = use_global_buffer

        # Fetched on initialization
        self.stock_name = None
        self.ltp = None
        self.lot_size = None
        self.expiry_dates = []
        self.alert_buffer = ALERT_BUFFER if use_global_buffer else []

    def fetch_page_json(self, expiry: str = None) -> dict:
        """Fetches page JSON (main or specific expiry)."""
        self.url = f"{self.BASE_URL}{self.stock_id}"
        if expiry:
            self.url += f"?expiry={expiry}"

        logging.info(f"🌐 Fetching data for URL: {self.url}")
        try:
            resp = requests.get(self.url, headers=self.headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logging.error(f"❌ Request failed for {self.url}: {e}")
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script_tag:
            logging.error("❌ Could not find __NEXT_DATA__ script")
            return {}

        return json.loads(script_tag.string)

    def initialize_stock_data(self):
        """Fetch stock details like LTP, lot size, expiry dates."""
        logging.info(f"🔄 Initializing stock data for {self.stock_id}...")
        data_json = self.fetch_page_json()
        if not data_json:
            raise RuntimeError(f"⚠️ Failed to initialize {self.stock_id}, no data returned")

        try:
            company_data = data_json["props"]["pageProps"]["data"]["company"]
            option_data = data_json["props"]["pageProps"]["data"]["optionChain"]

            self.stock_name = company_data["name"]
            self.ltp = company_data["liveData"]["ltp"]
            self.lot_size = option_data["aggregatedDetails"]["lotSize"]
            self.expiry_dates = option_data["aggregatedDetails"]["expiryDates"]

            logging.info(
                f"✅ Initialized {self.stock_name} | LTP: {self.ltp}, Lot size: {self.lot_size}, Expiries: {self.expiry_dates}"
            )
        except KeyError as e:
            raise RuntimeError(f"⚠️ Could not parse stock data for {self.stock_id}: Missing {e}")

    def find_closest_strike(self, option_chain, target_price):
        """Finds the strike closest to a target price using bisect."""
        strikes = [c["strikePrice"] / 100 for c in option_chain]  # Strikes are multiplied by 100 for some reason
        pos = bisect_left(strikes, target_price)
        logging.debug(f"🎯 Target: {target_price}, Closest strike index: {pos}")

        if pos == 0:
            return option_chain[0]
        if pos == len(strikes):
            return option_chain[-1]

        before = option_chain[pos - 1]
        after = option_chain[pos]
        return (
            before
            if abs(before["strikePrice"] / 100 - target_price) <= abs(after["strikePrice"] / 100 - target_price)
            else after
        )

    def process_expiry(self, expiry_date: str):
        """Process an expiry and send alerts if premiums cross threshold."""
        logging.info(f"📅 Processing expiry: {expiry_date}")
        data_json = self.fetch_page_json(expiry_date)
        if not data_json:
            logging.warning(f"⚠️ Skipping expiry {expiry_date} for {self.stock_id}, no data returned")
            return

        option_chain = data_json["props"]["pageProps"]["data"]["optionChain"]["optionContracts"]

        # Targets
        target_put = 0.905 * self.ltp
        target_call = 1.095 * self.ltp

        closest_put = self.find_closest_strike(option_chain, target_put)
        closest_call = self.find_closest_strike(option_chain, target_call)

        # Extract live data safely
        put_ltp = closest_put["pe"]["liveData"].get("ltp", 0) if closest_put.get("pe") else 0
        call_ltp = closest_call["ce"]["liveData"].get("ltp", 0) if closest_call.get("ce") else 0

        put_oi = closest_put["pe"]["liveData"].get("oi", 0) if closest_put.get("pe") else 0
        call_oi = closest_call["ce"]["liveData"].get("oi", 0) if closest_call.get("ce") else 0

        self.premium_lot_size = self.premium_lot_size if self.premium_lot_size else 2 * self.lot_size
        put_premium = self.premium_lot_size * put_ltp
        call_premium = self.premium_lot_size * call_ltp

        logging.info(
            f"{self.stock_name} | Expiry {expiry_date} | "
            f"PUT {closest_put['pe']['longDisplayName']} → {put_premium} (OI={put_oi}), "
            f"CALL {closest_call['ce']['longDisplayName']} → {call_premium} (OI={call_oi})"
        )

        # Alerts
        if put_oi > self.min_oi and put_premium > self.min_premium:
            msg = f"🚨 {self.stock_name} LTP {self.ltp} | Expiry {expiry_date} | {closest_put['pe']['longDisplayName']} | Premium {put_premium} | Lot {self.premium_lot_size} | Price {put_ltp} | OI {put_oi} | {self.url}"
            self.alert_buffer.append(msg)

        if call_oi > self.min_oi and call_premium > self.min_premium:
            msg = f"🚨 {self.stock_name} LTP {self.ltp} | Expiry {expiry_date} | {closest_call['ce']['longDisplayName']} | Premium {call_premium} | Lot {self.premium_lot_size} | Price {call_ltp} | OI {call_oi} | {self.url}"
            self.alert_buffer.append(msg)

    def flush_alerts(self):
        logging.info(f"🚀 Starting global alert flush.")
        flush_alert_buffer_global(self.alert_manager, self.alert_buffer)

    def run(self):
        """Run scraper for all expiry dates."""
        expiry_error = ""
        try:
            self.initialize_stock_data()
        except RuntimeError as e:
            message = f"❌ Failed to initialize {self.stock_id}: {e}"
            logging.error(message)
            self.alert_manager.send(message)
            return

        for expiry in self.expiry_dates:
            try:
                self.process_expiry(expiry)
            except Exception as error:
                message = f"Exception during process_expiry(): {error}"
                logging.error(message)
                expiry_error += message

        if expiry_error:
            self.alert_manager.send(expiry_error)

        if not self.use_global_buffer:
            self.flush_alerts()


if __name__ == "__main__":
    telegram_alert_obj = TelegramAlert()
    trackers_qty = {
        "nifty": [780, 30000],
        "infosys-ltd": [800],
        "hindustan-unilever-ltd": [600],
        "reliance-industries-ltd": [1000],
        "state-bank-of-india": [1500],
        "tata-consultancy-services-ltd": [350],
        "wipro-ltd": [6000],
        "itc-ltd": [3200],
        "bharti-airtel-ltd": [950],
        "icici-bank-ltd": [1400],
        "hdfc-bank-ltd": [2200],
        "axis-bank-ltd": [1250],
        "maruti-suzuki-india-ltd": [],
        "nestle-india-ltd": [],
        "apollo-hospitals-enterprise-ltd": [],
        "sun-pharmaceutical-industries-ltd": [],
        "coal-india-ltd": [],
        "grasim-industries-ltd": [],
        "dr-reddys-laboratories-ltd": [],
        "titan-company-ltd": [],
        "hdfc-standard-life-insurance-co-ltd": [],
        "sbi-life-insurance-company-ltd": [],
        "asian-paints-ltd": [],
        "ultratech-cement-ltd": [],
        "avenue-supermarts-ltd": [],
        "bajaj-auto-ltd": [],
        "bajaj-finserv-ltd": [],
        "britannia-industries-ltd": [],
        "bosch-ltd": [],
        "cipla-ltd": [],
        "dabur-india-ltd": [],
        "divis-laboratories-ltd": [],
        "godrej-consumer-products-ltd": [],
        "hero-motocorp-ltd": [],
        "jsw-steel-ltd": [],
        "lupin-ltd": [],
        "mrf-ltd": [],
        "marico-ltd": [],
        "page-industries-ltd": [],
        "sbi-cards-payment-services-ltd": [],
        "srf-ltd": [],
        "shree-cement-ltd": [],
        "tech-mahindra-ltd": [],
        "torrent-pharmaceuticals-ltd": [],
        "united-spirits-ltd": [],
        "colgatepalmolive-india-ltd": [],
        "icici-lombard-general-insurance-co-ltd": [],
        "power-grid-corporation-of-india-ltd": [],
        "tata-global-beverages-ltd": []
    }
    for tracker, qty in trackers_qty.items():
        logging.info(f"🚀 Starting scraper for {tracker}")
        if tracker in {"nifty"}:
            lot_size = qty[0] if len(qty) > 0 else None
        else:
            lot_size = None

        if tracker in {"nifty"}:
            min_premium = qty[1] if len(qty) > 1 else None
        else:
            min_premium = None

        scraper = OptionChainScraper(tracker, telegram_alert_obj, lot_size, min_premium, use_global_buffer=True)
        scraper.run()
        logging.info(f"✅ Completed scraper for {tracker}")

    logging.info(f"🚀 Starting global alert flush.")
    flush_alert_buffer_global(telegram_alert_obj, ALERT_BUFFER)
