"""
One-time script: Register Telegram webhook với ARIA backend.
Chạy sau khi deploy backend lên Cloud Run.

Usage:
  BACKEND_URL=https://hapura-command-backend-xxx.run.app \
  python setup_telegram_webhook.py
"""
import os
import httpx

TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SECRET  = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
BACKEND = os.environ.get("BACKEND_URL", "").rstrip("/")

if not TOKEN or not SECRET or not BACKEND:
    print("ERROR: Required env vars missing")
    print("  TELEGRAM_BOT_TOKEN=xxx TELEGRAM_WEBHOOK_SECRET=xxx BACKEND_URL=https://... python setup_telegram_webhook.py")
    exit(1)

webhook_url = f"{BACKEND}/api/v1/webhooks/telegram"
print(f"Registering webhook: {webhook_url}")

r = httpx.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={
        "url": webhook_url,
        "secret_token": SECRET,
        "allowed_updates": ["message"],
        "drop_pending_updates": True,
    },
    timeout=10,
)
print(f"Status: {r.status_code}")
print(r.json())

# Verify
info = httpx.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=5)
print("\nWebhook info:")
print(info.json())
