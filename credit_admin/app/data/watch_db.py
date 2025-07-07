import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'webui.db')
SCRIPT = os.path.join(BASE_DIR, 'sync_credits.py')

print("👀 Spouštím watch_db.py...")

class DBChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == DB_FILE:
            print("Změna databáze detekována. Spouštím synchronizaci...")
            subprocess.run(['python3', SCRIPT])

if __name__ == "__main__":
    event_handler = DBChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=BASE_DIR, recursive=False)
    observer.start()

    print(f"Sleduji změny databáze: {DB_FILE}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
