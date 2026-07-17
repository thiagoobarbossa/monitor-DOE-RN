from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

if not TOKEN or not CHAT_ID:
    print("Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no arquivo .env antes de testar.")
    raise SystemExit(1)

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "✅ Teste do Monitor DOE/RN: Telegram configurado corretamente.",
}

resp = requests.post(url, json=payload, timeout=15)
print("Status:", resp.status_code)
print(resp.text)

if resp.status_code == 200:
    print("Mensagem enviada com sucesso.")
else:
    print("Falha no envio. Confira token e chat_id.")
