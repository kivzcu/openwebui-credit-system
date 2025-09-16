import os

# Base directory for data files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # credit_admin/
DATA_DIR = os.path.join(BASE_DIR, "data")

# Database
DB_FILE = os.getenv("OPENWEBUI_DATABASE_PATH", "/root/.open-webui/webui.db")
DATABASE_URL = os.getenv("DATABASE_URL")
CREDIT_DATABASE_URL = os.getenv("CREDIT_DATABASE_URL")

# Script paths
SCRIPT_DIR = os.path.join(BASE_DIR, "app", "data")
SYNC_SCRIPT = os.path.join(SCRIPT_DIR, "sync_credits.py")

# Data files
CREDITS_FILE = os.path.join(DATA_DIR, "credits.json")
MODELS_FILE = os.path.join(DATA_DIR, "credits_models.json")
TRANSACTION_LOG_FILE = os.path.join(DATA_DIR, "transactions.json")
GROUPS_FILE = os.path.join(DATA_DIR, "credits_groups.json")
LOG_FILE = os.path.join(DATA_DIR, "credits_log.jsonl")
