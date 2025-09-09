# 📊 Groww Option Chain Scraper

This project scrapes option chain data from [Groww](https://groww.in/options/) for selected stocks and sends Telegram alerts when option premiums exceed defined thresholds.

---

## 🚀 Features
- Scrapes LTP (Last Traded Price) and option chain data.
- Finds strikes closest to 0.9 × LTP (Put) and 1.1 × LTP (Call).
- Sends Telegram alerts only if:
  - Option premium > threshold (default: ₹4000)
  - Open Interest (OI) > 50
- Runs automatically via GitHub Actions at:
  - **9:20 AM IST (03:50 UTC)**
  - **12:20 PM IST (07:20 UTC)**  
  on weekdays.

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
3. Configure Telegram Secrets

The scraper uses Telegram to send alerts. You need:

    TELEGRAM_BOT_TOKEN → From BotFather

    TELEGRAM_CHAT_ID → Chat/group ID where alerts should be sent

Add secrets in GitHub:

    Go to your repository on GitHub

    Navigate to Settings → Secrets and variables → Actions

    Add:

        TELEGRAM_BOT_TOKEN

        TELEGRAM_CHAT_ID

4. Run Locally

python option_scraper.py

⚡ GitHub Actions Automation

This repo includes a GitHub Actions workflow at .github/workflows/scraper.yml.

It will:

    Install dependencies

    Run the scraper

    Trigger automatically on schedule

To run manually:

    Go to your GitHub repo → Actions → Select workflow → Run workflow



✅ Example Alert

🚨 Infosys Ltd | Expiry 30-Sep-2025 | PUT INFY 30 Sep 1500 Put | Premium 8000 | OI 600

📝 Notes

    Logs are printed in GitHub Actions logs for debugging.

    Adjust the minimum premium/OI thresholds in the script if required.

    Timezone used by GitHub Actions is UTC, so schedules are converted from IST → UTC.
