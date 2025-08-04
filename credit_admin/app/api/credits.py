from fastapi import APIRouter, Request
import json
import sqlite3
import os
import fcntl
from datetime import datetime, timezone
from .credit_logic import calculate_and_deduct
from ..config import CREDITS_FILE, MODELS_FILE, GROUPS_FILE, DB_FILE, LOG_FILE, TRANSACTION_LOG_FILE
from ..database import CreditDatabase

router = APIRouter()

# -------------------------------
# PŮVODNÍ /api/users NECHÁVÁME CORE OPENWEBUI !!!
# -------------------------------

def append_log_entry(entry):
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a") as log_file:
        log_file.write(json.dumps(entry) + "\n")

# -------------------------------
# NOVÝ ENDPOINT PRO CREDIT MANAGEMENT
# -------------------------------
@router.get("/api/credits/users", tags=["credits"])
def get_users_with_credits():
    """Returns list of users with credits for Credit Management UI using new database system."""
    try:
        db = CreditDatabase()
        users = db.get_all_users_with_credits()
        
        # Format for the UI - maintain backward compatibility
        result = []
        for user in users:
            # Format groups for display (excluding system groups)
            display_groups = [g for g in user.get('groups', []) if not g.get('is_system_group', False)]
            group_name = ', '.join([g['name'] for g in display_groups]) if display_groups else None
            
            result.append({
                "id": user["id"],
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "credits": user.get("balance", 0),
                "total_default_credits": user.get("total_default_credits", 0),
                "groups": user.get("groups", []),
                "group_name": group_name,
                "default_credits": user.get("default_credits", 0),
                "role": group_name or "",  # Backward compatibility
                "avatar": f"https://i.pravatar.cc/36?u={user.get('email', '') or user.get('name', '')}"
            })
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# ENDPOINT PRO SEZNAM SKUPIN
# -------------------------------
@router.get("/api/credits/groups", tags=["credits"])
def get_credit_groups():
    """Returns list of groups with default credits using new database system."""
    try:
        db = CreditDatabase()
        groups = db.get_all_groups()
        
        # Filter out system groups for UI display
        result = []
        for group in groups:
            if not group.get('is_system_group', False):
                result.append({
                    "id": group["id"],
                    "name": group.get("name", ""),
                    "default_credits": group.get("default_credits", 0)
                })
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# ENDPOINT PRO SEZNAM MODELŮ
# -------------------------------
@router.get("/api/credits/models", tags=["credits"])
def get_credit_models():
    """Vrací seznam modelů s jejich náklady."""
    if os.path.exists(MODELS_FILE):
        with open(MODELS_FILE, 'r') as f:
            models_data = json.load(f)
    else:
        models_data = {}

    result = []
    for model_id, model in models_data.items():
        result.append({
            "id": model_id,
            "name": model.get("name", ""),
            "fixed_price": model.get("cost_per_token"),
            "variable_price": model.get("cost_per_second")
        })

    return result

# -------------------------------
# DALŠÍ ENDPOINT - PRO KOMPATIBILITU
# -------------------------------
@router.get("/api/credits-user-list", tags=["credits"])
def get_compatible_user_list():
    """Vrací seznam uživatelů pro selectboxy nebo jiné UI prvky."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, email, role FROM user")
        users_data = cursor.fetchall()
    except Exception as e:
        conn.close()
        return {"error": str(e)}

    conn.close()

    result = []
    for user_id, name, email, role in users_data:
        result.append({
            "id": user_id,
            "username": name or "",
            "email": email or "",
            "is_admin": role == "admin"
        })

    return result

# --- NOVÝ ENDPOINT PRO ULOŽENÍ KREDITŮ ---
@router.post("/api/credits/update", tags=["credits"])
async def update_credits(request: Request):
    """Aktualizace kreditů uživatele a zápis do credits.json"""
    data = await request.json()
    user_id = data.get("id")
    new_credits = data.get("credits")
    actor = data.get("actor", "unknown")

    if not user_id or new_credits is None:
        return {"error": "Chybí ID nebo počet kreditů"}

    # Načti aktuální data
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as f:
            credits_data = json.load(f)
    else:
        credits_data = {"users": {}}

    # Uprav kredity daného uživatele
    if user_id not in credits_data["users"]:
        credits_data["users"][user_id] = {}

    credits_data["users"][user_id]["balance"] = new_credits

    # Zapiš zpět do souboru
    with open(CREDITS_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(credits_data, f, indent=4)
        fcntl.flock(f, fcntl.LOCK_UN)

    # Log změny
    append_log_entry({
        "type": "user_credit_update",
        "actor": actor,
        "user_id": user_id,
        "new_credits": new_credits
    })

    print("ZAPISUJE SE DO:", CREDITS_FILE)
    
    return {"status": "success", "id": user_id, "credits": new_credits}

# --- NOVÝ ENDPOINT PRO ULOŽENÍ KREDITŮ SKUPINY ---
@router.post("/api/credits/groups/update", tags=["credits"])
async def update_group_credits(request: Request):
    """Aktualizace výchozích kreditů pro skupinu a zápis do credits_groups.json"""
    data = await request.json()
    group_id = data.get("id")
    new_credits = data.get("default_credits")
    actor = data.get("actor", "unknown")

    if not group_id or new_credits is None:
        return {"error": "Chybí ID nebo počet kreditů"}

    # Načti aktuální data
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r") as f:
            groups_data = json.load(f)
    else:
        groups_data = {}

    # Uprav kredity dané skupiny
    if group_id not in groups_data:
        return {"error": "Skupina neexistuje"}

    groups_data[group_id]["default_credits"] = new_credits

    # Zapiš zpět do souboru
    with open(GROUPS_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(groups_data, f, indent=4)
        fcntl.flock(f, fcntl.LOCK_UN)

    # Log změny
    append_log_entry({
        "type": "group_update",
        "actor": actor,
        "group_id": group_id,
        "default_credits": new_credits
    })

    return {"status": "success", "id": group_id, "default_credits": new_credits}

# --- NOVÝ ENDPOINT PRO ULOŽENÍ NÁKLADŮ MODELU ---
@router.post("/api/credits/models/update", tags=["credits"])
async def update_model_costs(request: Request):
    """Aktualizace nákladů na model a zápis do credits_models.json"""
    data = await request.json()
    model_id = data.get("id")
    fixed_price = data.get("fixed_price")
    variable_price = data.get("variable_price")
    actor = data.get("actor", "unknown")


    if not model_id or fixed_price is None or variable_price is None:
        return {"error": "Chybí ID nebo ceny"}

    if os.path.exists(MODELS_FILE):
        with open(MODELS_FILE, "r") as f:
            models_data = json.load(f)
    else:
        models_data = {}

    if model_id not in models_data:
        return {"error": "Model neexistuje"}

    models_data[model_id]["cost_per_token"] = fixed_price
    models_data[model_id]["cost_per_second"] = variable_price

    with open(MODELS_FILE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(models_data, f, indent=4)
        fcntl.flock(f, fcntl.LOCK_UN)

    append_log_entry({
        "type": "model_update",
        "actor": actor,
        "model_id": model_id,
        "fixed_price": fixed_price,
        "variable_price": variable_price
    })

    return {
        "status": "success",
        "id": model_id,
        "fixed_price": fixed_price,
        "variable_price": variable_price
    }

# --- NOVÝ ENDPOINT PRO ZÍSKÁNÍ SYSTÉMOVÝCH LOGŮ ---
@router.get("/api/credits/system-logs", tags=["credits"])
def get_system_logs(limit: int = 100):
    """Vrací posledních N záznamů ze systémových logů."""
    if not os.path.exists(LOG_FILE):
        return {"logs": []}

    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            # Vezmeme posledních `limit` záznamů
            recent_lines = lines[-limit:]
            logs = [json.loads(line) for line in recent_lines]
    except Exception as e:
        return {"error": f"Error reading logs: {str(e)}"}

    return {"logs": logs}

@router.get("/api/credits/transactions", tags=["credits"])
def get_transaction_logs(limit: int = 100):
    """Vrací posledních N záznamů z transakčního logu."""
    if not os.path.exists(TRANSACTION_LOG_FILE):
        return {"transactions": []}

    try:
        with open(TRANSACTION_LOG_FILE, "r") as f:
            data = json.load(f)
            transactions = data.get("transactions", [])[-limit:]
    except Exception as e:
        return {"error": f"Error reading transaction log: {str(e)}"}

    return {"transactions": transactions}

@router.post("/api/credits/deduct", tags=["credits"])
async def deduct_credits(request: Request):
    """
    Strhne kredity uživateli za požadavek podle délky trvání.
    """
    data = await request.json()
    user_id = data.get("user_id")
    duration = data.get("duration_seconds")

    if not user_id or duration is None:
        return {"error": "Chybí user_id nebo duration_seconds"}

    try:
        charged, remaining = calculate_and_deduct(user_id, float(duration))
    except ValueError as e:
        return {"error": str(e)}

    return {
        "charged_amount": charged,
        "remaining_balance": remaining,
        "message": "Credits deducted successfully."
    }
