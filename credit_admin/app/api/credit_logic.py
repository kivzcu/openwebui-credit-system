import json
import os
from datetime import datetime
import logging

log = logging.getLogger(__name__)

from ..config import CREDITS_FILE, MODELS_FILE, TRANSACTION_LOG_FILE


def get_pricing_model(model_id: str | None = None):
    """Get pricing model for a specific model ID."""
    default_pricing = {
        "cost_per_request": 2,
        "cost_per_second": 1
    }

    if not model_id:
        return default_pricing

    if os.path.exists(MODELS_FILE):
        try:
            with open(MODELS_FILE, "r") as f:
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
            print(f"Error loading {MODELS_FILE}: {e}")

    return default_pricing


def calculate_cost(duration_seconds: float, pricing: dict):
    return pricing["cost_per_request"] + int(duration_seconds) * pricing["cost_per_second"]

def calculate_and_deduct(user_id: str, duration_seconds: float, model_id: str | None = None):
    """Calculate cost and deduct credits from user balance."""
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"users": {}}

    if user_id not in data["users"]:
        raise ValueError(f"User {user_id} does not exist.")

    user = data["users"][user_id]
    balance = user.get("balance", 0)

    pricing = get_pricing_model(model_id)
    total_cost = calculate_cost(duration_seconds, pricing)

    charged_amount = min(balance, total_cost)
    user["balance"] = balance - charged_amount
    
    reason = (
        f"Request charge for model '{model_id}' ({pricing['cost_per_request']} + "
        f"{int(duration_seconds)}×{pricing['cost_per_second']})"
    )
    
    if charged_amount < total_cost:
        reason += f" - Insufficient credits: charged {charged_amount} instead of {total_cost}"

    # Add to user history
    history_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "deduct",
        "amount": charged_amount,
        "reason": reason
    }

    if "history" not in user:
        user["history"] = []
    user["history"].append(history_entry)

    # Save credits file
    with open(CREDITS_FILE, "w") as f:
        json.dump(data, f, indent=4)

    # Log transaction
    _log_transaction(user_id, charged_amount, user["balance"], model_id, history_entry["timestamp"])

    return charged_amount, user["balance"]


def _log_transaction(user_id: str, amount: float, balance_after: float, model_id: str | None, timestamp: str):
    """Log transaction to global transaction log."""
    transaction_entry = {
        "timestamp": timestamp,
        "user_id": user_id,
        "amount": amount,
        "balance_after": balance_after,
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

