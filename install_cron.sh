#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
CRON_BEGIN="# BEGIN option_writer managed cron"
CRON_END="# END option_writer managed cron"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found in PATH and PYTHON_BIN was not provided." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.example to .env and fill in Telegram credentials first." >&2
  exit 1
fi

CRON_BLOCK=$(cat <<EOF
${CRON_BEGIN}
15 3 * * 1-5 cd ${SCRIPT_DIR} && set -a && . ${ENV_FILE} && set +a && ${PYTHON_BIN} tradingview_returns.py
55 3 * * 1-5 cd ${SCRIPT_DIR} && set -a && . ${ENV_FILE} && set +a && ${PYTHON_BIN} option_writer.py
30 7 * * 1-5 cd ${SCRIPT_DIR} && set -a && . ${ENV_FILE} && set +a && ${PYTHON_BIN} option_writer.py
${CRON_END}
EOF
)

EXISTING_CRONTAB="$(mktemp)"
FILTERED_CRONTAB="$(mktemp)"
trap 'rm -f "${EXISTING_CRONTAB}" "${FILTERED_CRONTAB}"' EXIT

if crontab -l > "${EXISTING_CRONTAB}" 2>/dev/null; then
  awk -v begin="${CRON_BEGIN}" -v end="${CRON_END}" '
    $0 == begin { skip=1; next }
    $0 == end { skip=0; next }
    !skip { print }
  ' "${EXISTING_CRONTAB}" > "${FILTERED_CRONTAB}"
else
  : > "${FILTERED_CRONTAB}"
fi

{
  cat "${FILTERED_CRONTAB}"
  if [[ -s "${FILTERED_CRONTAB}" ]]; then
    echo
  fi
  echo "${CRON_BLOCK}"
} | crontab -

echo "Installed option_writer cron jobs:"
echo "${CRON_BLOCK}"
