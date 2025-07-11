import os

APP_DIR = os.path.dirname(__file__)
SCRIPT_DIR = os.path.join(APP_DIR, "data")
DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../data"))
DB_FILE = "/root/.open-webui/webui.db"
SYNC_SCRIPT = os.path.join(SCRIPT_DIR, "sync_credits.py")
CREDITS_FILE = os.path.join(DATA_DIR, "credits.json")
MODELS_FILE = os.path.join(DATA_DIR, "credits_models.json")
TRANSACTION_LOG_FILE = os.path.join(DATA_DIR, "transactions.json")
GROUPS_FILE = os.path.join(DATA_DIR, "credits_groups.json")
LOG_FILE = os.path.join(DATA_DIR, "credits_log.jsonl")
