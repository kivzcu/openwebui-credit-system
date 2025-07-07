import json
import os
import fcntl
from datetime import datetime, timezone
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import CREDITS_FILE, GROUPS_FILE, LOG_FILE

MAX_HISTORY = 10


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {path} is empty or invalid.")
            return {}


def save_json_file(path, data):
    with open(path, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=4)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def append_log(entry):
    entry['timestamp'] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\n")


def reset_all_user_credits():
    credits_data = load_json_file(CREDITS_FILE)
    groups_data = load_json_file(GROUPS_FILE)

    updated_users = 0

    for user_id, user in credits_data.get("users", {}).items():
        group_id = user.get("group", "default")
        default_credits = groups_data.get(group_id, {}).get("default_credits")
        if default_credits is not None:
            user['balance'] = default_credits
            user.setdefault('history', []).append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "monthly-reset",
                "amount": default_credits,
                "reason": f"Monthly reset based on group '{group_id}'"
            })
            user['history'] = user['history'][-MAX_HISTORY:]
            updated_users += 1

    save_json_file(CREDITS_FILE, credits_data)

    append_log({
        "type": "monthly_reset",
        "actor": "system",
        "message": f"Monthly credit reset applied to {updated_users} users."
    })

    print(f"Monthly reset applied to {updated_users} users.")


if __name__ == '__main__':
    reset_all_user_credits()
