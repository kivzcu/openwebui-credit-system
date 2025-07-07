import json
import os
import sqlite3
import fcntl
from datetime import datetime, timezone
import random
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import CREDITS_FILE, GROUPS_FILE, MODELS_FILE, DB_FILE


print(f"🔧 Načítám data z:\n{CREDITS_FILE}\n{GROUPS_FILE}\n{MODELS_FILE}\n{DB_FILE}")

DEFAULT_CREDITS = 1000
DEFAULT_GROUP_ID = "default"
DEFAULT_GROUP_NAME = "Uživatelé"
MAX_HISTORY = 10

def check_database_tables():
    """Zkontroluje, zda databázové tabulky existují."""
    if not os.path.exists(DB_FILE):
        print(f"❌ Error: Database file {DB_FILE} not found!")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    required_tables = ['user', 'group', 'model']
    missing_tables = []
    
    for table_name in required_tables:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        if not cursor.fetchone():
            missing_tables.append(table_name)
    
    conn.close()
    
    if missing_tables:
        print(f"❌ Error: Required database tables are missing: {', '.join(missing_tables)}")
        print("Please ensure the database is properly initialized with all required tables.")
        sys.exit(1)
    
    print("✅ Database tables verified.")

def load_credits():
    if not os.path.exists(CREDITS_FILE):
        return {"users": {}}
    with open(CREDITS_FILE, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {CREDITS_FILE} is empty or invalid. Reinitializing.")
                data = {"users": {}}
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    if "users" not in data:
        data["users"] = {}
    return data

def save_credits(data):
    with open(CREDITS_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=4)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return {}
    with open(GROUPS_FILE, 'r') as f:
        return json.load(f)

def save_groups(data):
    with open(GROUPS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_models():
    if not os.path.exists(MODELS_FILE):
        return {}
    with open(MODELS_FILE, 'r') as f:
        return json.load(f)

def save_models(data):
    with open(MODELS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def sync_users_with_db():
    credits_data = load_credits()
    groups_data = load_groups()

    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found!")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM user")
    users = cursor.fetchall()

    cursor.execute('SELECT id, user_ids FROM "group"')
    group_data = cursor.fetchall()
    user_group_map = {}
    for group_id, user_ids_json in group_data:
        try:
            if isinstance(user_ids_json, str):
                user_ids = json.loads(user_ids_json.strip())
            else:
                user_ids = []
            for uid in user_ids:
                user_group_map[uid] = group_id
        except json.JSONDecodeError as e:
            print(f"Failed to parse user_ids for group {group_id}: {e}")
            continue

    for user_id, name, email in users:
        group_id = user_group_map.get(user_id, DEFAULT_GROUP_ID)
        group_info = groups_data.get(group_id, {})
        default_credits = group_info.get("default_credits", DEFAULT_CREDITS)

        if user_id not in credits_data['users']:
            credits_data['users'][user_id] = {
                "balance": default_credits,
                "history": [
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "action": "add",
                        "amount": default_credits,
                        "reason": "Initial allocation"
                    }
                ],
                "group": group_id
            }
            print(f"Added new user {user_id} ({email}) with {default_credits} credits and group {group_id}.")
        else:
            credits_data['users'][user_id]['group'] = group_id

    save_credits(credits_data)
    conn.close()

def sync_groups_with_db():
    groups_data = load_groups()
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found!")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM "group"')
    groups = cursor.fetchall()

    for group_id, name in groups:
        if group_id not in groups_data:
            groups_data[group_id] = {
                "name": name,
                "default_credits": DEFAULT_CREDITS
            }
            print(f"Added new group {group_id} ({name}) with default credits {DEFAULT_CREDITS}.")

    if DEFAULT_GROUP_ID not in groups_data:
        groups_data[DEFAULT_GROUP_ID] = {
            "name": DEFAULT_GROUP_NAME,
            "default_credits": DEFAULT_CREDITS
        }
        print(f"Added default group '{DEFAULT_GROUP_ID}' ({DEFAULT_GROUP_NAME}) with default credits {DEFAULT_CREDITS}.")

    save_groups(groups_data)
    conn.close()

def sync_models_with_db():
    models_data = load_models()
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found!")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM model")
    models = cursor.fetchall()

    for model_id, name in models:
        if model_id not in models_data:
            models_data[model_id] = {
                "name": name,
                "cost_per_token": 1,
                "cost_per_second": 1
            }
            print(f"Added new model {model_id} ({name}) with cost 1 per token and 1 per second.")

    save_models(models_data)
    conn.close()

def assign_user_to_group(user_id, group_id):
    data = load_credits()
    groups = load_groups()
    if user_id not in data['users']:
        print(f"User {user_id} not found.")
        return
    if group_id not in groups:
        print(f"Group {group_id} not found.")
        return
    data['users'][user_id]['group'] = group_id
    print(f"Assigned user {user_id} to group {group_id}.")
    save_credits(data)

def set_credits_for_group(group_id, amount):
    data = load_credits()
    groups = load_groups()
    if group_id not in groups:
        print(f"Group {group_id} not found.")
        return
    groups[group_id]['default_credits'] = amount
    for uid, user in data['users'].items():
        if user.get('group') == group_id:
            user['balance'] = amount
            user['history'].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "group-set",
                "amount": amount,
                "reason": f"Credits set by group {group_id}"
            })
            user['history'] = user['history'][-MAX_HISTORY:]
            print(f"Set user {uid}'s credits to {amount} based on group {group_id}.")
    save_credits(data)
    save_groups(groups)

if __name__ == "__main__":
    check_database_tables()
    sync_users_with_db()
    sync_groups_with_db()
    sync_models_with_db()

    # Test block byl odstraněn pro zachování ruční správy kreditů

    print("Synchronization complete.")
