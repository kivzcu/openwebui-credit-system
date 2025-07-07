import json
import os
from datetime import datetime
from fastapi import Request
#from open_webui.utils.auth import get_verified_user
import logging
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDITS_FILE = os.path.abspath(os.path.join(BASE_DIR, "../data/credits.json"))
PRICING_FILE = os.path.abspath(os.path.join(BASE_DIR, "../data/credits_models.json"))
TRANSACTION_LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "../data/transactions.json"))

def calculate_and_deduct_new(request: Request, user_id: str, model_id: str):
    response_data = getattr(request.state, "model_response", {})
    usage = response_data.get("usage", {})
    duration_ns = usage.get("total_duration", 0)
    duration_seconds = duration_ns / 1_000_000_000

    log.debug(f"duration_ns: {duration_ns}, seconds: {duration_seconds}")
    return calculate_and_deduct(user_id, duration_seconds, model_id)

def get_pricing_model(model_id: str = None):
    default_pricing = {
        "cost_per_request": 2,
        "cost_per_second": 1
    }

    if not model_id:
        return default_pricing

    if os.path.exists(PRICING_FILE):
        try:
            with open(PRICING_FILE, "r") as f:
                pricing_data = json.load(f)

            model_pricing = pricing_data.get(model_id)
            if (
                model_pricing
                and isinstance(model_pricing.get("cost_per_token"), (int, float))
                and isinstance(model_pricing.get("cost_per_second"), (int, float))
            ):
                return {
                    "cost_per_request": model_pricing["cost_per_token"],
                    "cost_per_second": model_pricing["cost_per_second"]
                }
        except Exception as e:
            print(f"Chyba při načítání {PRICING_FILE}: {e}")

    return default_pricing


def calculate_cost(duration_seconds: float, pricing: dict):
    return pricing["cost_per_request"] + int(duration_seconds) * pricing["cost_per_second"]

def calculate_and_deduct(user_id: str, duration_seconds: float, model_id: str = None):
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"users": {}}

    if user_id not in data["users"]:
        raise ValueError(f"Uživatel {user_id} neexistuje.")

    user = data["users"][user_id]
    balance = user.get("balance", 0)

    pricing = get_pricing_model(model_id)
    total_cost = calculate_cost(duration_seconds, pricing)

    charged_amount = 0

    if balance >= total_cost:
        user["balance"] = balance - total_cost
        charged_amount = total_cost
        reason = (
            f"Request charge for model '{model_id}' ({pricing['cost_per_request']} + "
            f"{int(duration_seconds)}×{pricing['cost_per_second']})"
        )
    else:
        charged_amount = balance
        user["balance"] = 0
        reason = (
            f"Insufficient credits for model '{model_id}': charged {charged_amount} "
            f"instead of {total_cost}."
        )

    history_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "deduct",
        "amount": charged_amount,
        "reason": reason
    }

    if "history" not in user:
        user["history"] = []
    user["history"].append(history_entry)

    with open(CREDITS_FILE, "w") as f:
        json.dump(data, f, indent=4)

    # --- Globální transakční log ---
    transaction_entry = {
        "timestamp": history_entry["timestamp"],
        "user_id": user_id,
        "amount": charged_amount,
        "balance_after": user["balance"],
        "model": model_id,
    }

    if os.path.exists(TRANSACTION_LOG_FILE):
        with open(TRANSACTION_LOG_FILE, "r") as f:
            transaction_data = json.load(f)
    else:
        transaction_data = {"transactions": []}

    transaction_data["transactions"].append(transaction_entry)

    with open(TRANSACTION_LOG_FILE, "w") as f:
        json.dump(transaction_data, f, indent=4)


    return charged_amount, user["balance"]

def check_minimum_balance(user_id: str, model_id: str):
    pricing = get_pricing_model(model_id)
    min_required = pricing["cost_per_request"]

    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as f:
            credits_data = json.load(f)
    else:
        credits_data = {"users": {}}

    user_data = credits_data.get("users", {}).get(user_id)
    if not user_data:
        raise ValueError("Uživatel nenalezen v systému kreditů.")

    balance = user_data.get("balance", 0)

    if balance < min_required:
        raise ValueError(
            f"Lack of credits. Contact the OpenWebUI administrator."
        )

