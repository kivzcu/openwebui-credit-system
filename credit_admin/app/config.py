import os

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "webui.db")
SYNC_SCRIPT = os.path.join(DATA_DIR, "sync_credits.py")
CREDITS_FILE = os.path.join(DATA_DIR, "credits.json")
MODELS_FILE = os.path.join(DATA_DIR, "credits_models.json")
TRANSACTION_LOG_FILE = os.path.join(DATA_DIR, "transactions.json")
GROUPS_FILE = os.path.join(DATA_DIR, "credits_groups.json")
LOG_FILE = os.path.join(DATA_DIR, "credits_log.jsonl")
