import os
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import credits
from app.data.monthly_credit_reset import reset_all_user_credits

# 🔁 Nové importy pro sledování databáze
import subprocess, time
from threading import Thread
from datetime import datetime
from app.config import DB_FILE, SYNC_SCRIPT, DATA_DIR

def schedule_monthly_reset():
    while True:
        now = datetime.utcnow()
        if now.day == 1 and now.hour == 0 and now.minute == 0 and now.second == 0:
            print("📅 Spouštím měsíční reset kreditů...")
            reset_all_user_credits()
            time.sleep(1)
        time.sleep(1)

def start_scheduler():
    Thread(target=schedule_monthly_reset, daemon=True).start()

from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler

app = FastAPI()

# ⬇️ Cesty ke statickým souborům
static_dir = os.path.join(os.path.dirname(__file__), "static")
index_file = os.path.join(static_dir, "index.html")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    return FileResponse(index_file)

# ⬇️ Router pro kredity
app.include_router(credits.router)

# ⬇️ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⬇️ Databázový pozorovatel (watcher)
class DBChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == DB_FILE:
            print("🟡 Změna databáze detekována, spouštím synchronizaci...")
            subprocess.run(["python3", SYNC_SCRIPT])

def watch_db():
    print("👁️ Watchdog aktivován")
    observer = Observer()
    observer.schedule(DBChangeHandler(), path=DATA_DIR, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()

@app.on_event("startup")
def on_startup():
    print("🛠️ První spuštění synchronizace kreditů...")
    subprocess.run(["python3", SYNC_SCRIPT])
    Thread(target=watch_db, daemon=True).start()
    start_scheduler()
    print("🚀 Watcher + Scheduler spuštěny při startu")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

