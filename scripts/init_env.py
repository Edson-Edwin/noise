"""Create local secrets without printing or overwriting them."""
from pathlib import Path
import os
import secrets

path = Path(".env")
password = secrets.token_hex(24)
content = (f"POSTGRES_PASSWORD={password}\n"
           f"DATABASE_URL=postgresql+psycopg://noise:{password}@db:5432/noise_monitor\n"
           f"DEVICE_API_KEY={secrets.token_hex(32)}\n"
           f"DASHBOARD_API_KEY={secrets.token_hex(32)}\n"
           "DEVICE_ID=esp32-01\nPORT=8000\nRETENTION_DAYS=30\nSTALE_AFTER_SECONDS=30\n")
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(".env already exists; left unchanged.")
with os.fdopen(fd, "w") as file:
    file.write(content)
print("Created private .env. Keep it out of Git and shared archives.")
