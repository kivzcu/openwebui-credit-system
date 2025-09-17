import os

# Base directory for data files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # credit_admin/
DATA_DIR = os.path.join(BASE_DIR, "data")

# Database
DB_FILE = os.getenv("OPENWEBUI_DATABASE_PATH", "")
DATABASE_URL = os.getenv("DATABASE_URL")
CREDIT_DATABASE_URL = os.getenv("CREDIT_DATABASE_URL")