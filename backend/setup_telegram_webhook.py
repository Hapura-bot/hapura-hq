"""
One-time script: Register Telegram webhook với ARIA backend.
Chạy sau khi deploy backend lên Cloud Run.

Usage:
  BACKEND_URL=https://hapura-command-backend-xxx.run.app \
  python setup_telegram_webhook.py
"""
import os
import httpx

TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN",   "REDACTED_TELEGRAM_TOKEN")
SECRET  = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "aria-hq-secret-2026")
BACKEND = os.environ.get("BACKEND_URL", "").rstrip("/")

if not BACKEND:
    print("ERROR: Set BACKEND_URL environment variable")
    print("  Example: BACKEND_URL=https://hapura-command-backend-xxx.run.app python setup_telegram_webhook.py")
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
