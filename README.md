# 📊 Groww Option Chain Scraper

This project scrapes option chain data from [Groww](https://groww.in/options/) for selected stocks, sends Telegram alerts when option premiums exceed defined thresholds, and can also send a separate TradingView returns snapshot.

---

## 🚀 Features
- Scrapes LTP (Last Traded Price) and option chain data.
- Finds strikes closest to 0.9 × LTP (Put) and 1.1 × LTP (Call).
- Sends a separate TradingView futures return summary.
- Sends Telegram alerts only if:
  - Option premium > threshold (default: ₹4000)
  - Open Interest (OI) > 50
- Supports local cron as the primary scheduler.
- Keeps rotating logs for 2 days under `logs/`.

---

## ⚙️ Setup

### 1. Clone Repository
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```
2. Install Dependencies

Make sure you have Python 3.11+.
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
3. Configure Telegram Environment Variables

This repo reads Telegram credentials from environment variables:

    TELEGRAM_BOT_TOKEN -> From BotFather

    TELEGRAM_CHAT_ID -> Chat/group ID where alerts should be sent

For local runs:

```bash
cp .env.example .env
```

Then edit `.env` with your real values. `.env` is ignored by git and will not be uploaded.

4. Run Locally

Run the option writer:

```bash
set -a
. ./.env
set +a
python option_writer.py
```

Run the TradingView returns script:

```bash
set -a
. ./.env
set +a
python tradingview_returns.py
```

## ⏰ Cron Setup

Cron is the primary automation path for this repo.

The intended weekday schedules are:

- `tradingview_returns.py` at **8:45 AM IST** = **03:15 UTC**
- `option_writer.py` at **9:25 AM IST** = **03:55 UTC**
- `option_writer.py` at **1:00 PM IST** = **07:30 UTC**

Install the managed cron block with:

```bash
chmod +x install_cron.sh
./install_cron.sh
```

The installer:

- Requires `.env` to exist first.
- Preserves unrelated existing crontab entries.
- Replaces only the cron block managed by this repo.
- Uses `python3` by default.

If you use a virtual environment, point the installer at it:

```bash
PYTHON_BIN=/home/ubuntu/option_writer/.venv/bin/python ./install_cron.sh
```

To confirm the installed jobs:

```bash
crontab -l
```

The installed weekday cron entries are:

```cron
15 3 * * 1-5 cd /home/ubuntu/option_writer && set -a && . /home/ubuntu/option_writer/.env && set +a && /usr/bin/python3 tradingview_returns.py
55 3 * * 1-5 cd /home/ubuntu/option_writer && set -a && . /home/ubuntu/option_writer/.env && set +a && /usr/bin/python3 option_writer.py
30 7 * * 1-5 cd /home/ubuntu/option_writer && set -a && . /home/ubuntu/option_writer/.env && set +a && /usr/bin/python3 option_writer.py
```

⚡ GitHub Actions Automation

This repo includes a GitHub Actions workflow at .github/workflows/scraper.yml.

GitHub Actions is kept for manual fallback only. The schedule block is intentionally commented out to avoid duplicate automation with cron.

To use GitHub Actions manually:

    Go to your repository on GitHub

    Navigate to Settings -> Secrets and variables -> Actions

    Add:

        TELEGRAM_BOT_TOKEN

        TELEGRAM_CHAT_ID

    Go to Actions -> Select workflow -> Run workflow

The workflow currently runs `option_writer.py` manually with those secrets.

## 🪵 Logging

Logs are stored in the repo under `logs/`.

- `logs/option_writer.log`
- `logs/tradingview_returns.log`

Log files rotate daily and keep 2 retained backups. Older rotated files are deleted automatically by Python's rotating log handler.


✅ Example Alert

🚨 Infosys Ltd | Expiry 30-Sep-2025 | PUT INFY 30 Sep 1500 Put | Premium 8000 | OI 600

📝 Notes

    Adjust the minimum premium/OI thresholds in the script if required.

    Cron expressions use UTC, so the README lists both IST and UTC times.
