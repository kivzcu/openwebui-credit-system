"""
Optimized API endpoints for credit management system.
Uses SQLite database instead of JSON files and provides targeted endpoints.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional, List
import sqlite3
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import db
from app.config import DB_FILE  # OpenWebUI database for user sync

router = APIRouter()

# Request/Response models
class CreditUpdateRequest(BaseModel):
    user_id: str
    credits: float
    actor: str = "admin"

class ModelPricingRequest(BaseModel):
    model_id: str
    context_price: float
    generation_price: float
    actor: str = "admin"

class GroupUpdateRequest(BaseModel):
    group_id: str
    name: str
    default_credits: float
    actor: str = "admin"

class CreditDeductionRequest(BaseModel):
    user_id: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    actor: str = "auto-system"

# User-specific endpoints (optimized for extensions)
@router.get("/api/credits/user/{user_id}", tags=["credits"])
async def get_user_credits(user_id: str):
    """Get specific user's credit information - optimized for extensions"""
    user_data = db.get_user_credits(user_id)
    
    if not user_data:
        # Try to sync from OpenWebUI database first
        await sync_user_from_openwebui(user_id)
        user_data = db.get_user_credits(user_id)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user_data["id"],
        "credits": user_data["balance"],
        "group_id": user_data["group_id"],
        "group_name": user_data.get("group_name"),
        "default_credits": user_data.get("default_credits", 0)
    }

@router.get("/api/credits/model/{model_id}", tags=["credits"])
async def get_model_pricing(model_id: str):
    """Get specific model's pricing information - optimized for extensions"""
    model_data = db.get_model_pricing(model_id)
    
    if not model_data:
        # Auto-create model with default pricing if not exists
        db.update_model_pricing(model_id, model_id, 0.001, 0.004)  # Updated default pricing
        model_data = db.get_model_pricing(model_id)
        db.log_action("model_auto_created", "system", f"Auto-created model {model_id} with default pricing")
        
        if not model_data:  # Still None after creation - something went wrong
            raise HTTPException(status_code=500, detail="Failed to create model pricing")
    
    return {
        "id": model_data["id"],
        "name": model_data["name"],
        "context_price": model_data["context_price"],
        "generation_price": model_data["generation_price"]
    }

# Optimized credit deduction endpoint for extensions
@router.post("/api/credits/deduct-tokens", tags=["credits"])
async def deduct_credits_for_tokens(request: CreditDeductionRequest):
    """
    Optimized endpoint for credit deduction based on token usage.
    Used by extensions instead of the old inefficient method.
    """
    # Get user and model data efficiently
    user_data = db.get_user_credits(request.user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    model_data = db.get_model_pricing(request.model_id)
    if not model_data:
        raise HTTPException(status_code=404, detail="Model pricing not found")
    
    # Calculate cost
    prompt_cost = request.prompt_tokens * model_data["context_price"]
    completion_cost = request.completion_tokens * model_data["generation_price"]
    total_cost = prompt_cost + completion_cost
    
    # Deduct credits
    deducted, new_balance = db.deduct_credits(
        user_id=request.user_id,
        amount=total_cost,
        actor=request.actor,
        reason=f"Token usage: {request.prompt_tokens} prompt + {request.completion_tokens} completion tokens",
        model_id=request.model_id,
        prompt_tokens=request.prompt_tokens,
        completion_tokens=request.completion_tokens
    )
    
    return {
        "success": True,
        "cost": total_cost,
        "deducted": deducted,
        "new_balance": new_balance,
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost
    }

# Batch endpoint for admin UI (when you need multiple users/models)
@router.get("/api/credits/users", tags=["credits"])
async def get_all_users_with_credits():
    """Get all users with credit information - for admin UI"""
    # First sync users from OpenWebUI
    await sync_all_users_from_openwebui()
    
    users = db.get_all_users_with_credits()
    
    # Get additional user info from OpenWebUI database
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM user")
            openwebui_users = {row["id"]: {"name": row["name"], "email": row["email"]} for row in cursor.fetchall()}
    except Exception:
        openwebui_users = {}
    
    result = []
    for user in users:
        openwebui_info = openwebui_users.get(user["id"], {})
        result.append({
            "id": user["id"],
            "name": openwebui_info.get("name", "Unknown"),
            "email": openwebui_info.get("email", ""),
            "credits": user["balance"],
            "group_id": user["group_id"],
            "role": user.get("group_name", "Unknown"),
            "avatar": f"https://i.pravatar.cc/36?u={openwebui_info.get('email', user['id'])}"
        })
    
    return result

@router.get("/api/credits/models", tags=["credits"])
async def get_all_models():
    """Get all model pricing information - for admin UI"""
    models = db.get_all_models()
    return [
        {
            "id": model["id"],
            "name": model["name"],
            "context_price": model["context_price"],
            "generation_price": model["generation_price"]
        }
        for model in models
    ]

@router.get("/api/credits/groups", tags=["credits"])
async def get_all_groups():
    """Get all credit groups - for admin UI"""
    groups = db.get_all_groups()
    return [
        {
            "id": group["id"],
            "name": group["name"],
            "default_credits": group["default_credits"]
        }
        for group in groups
    ]

# Update endpoints
@router.post("/api/credits/update", tags=["credits"])
async def update_user_credits(request: CreditUpdateRequest):
    """Update user's credit balance"""
    success = db.update_user_credits(
        user_id=request.user_id,
        new_balance=request.credits,
        actor=request.actor,
        transaction_type="manual_update",
        reason=f"Manual credit update by {request.actor}"
    )
    
    if success:
        db.log_action("user_credit_update", request.actor, f"Updated user {request.user_id} credits to {request.credits}")
        return {"status": "success", "id": request.user_id, "credits": request.credits}
    else:
        raise HTTPException(status_code=500, detail="Failed to update credits")

@router.post("/api/credits/models/update", tags=["credits"])
async def update_model_pricing(request: ModelPricingRequest):
    """Update model pricing"""
    success = db.update_model_pricing(
        model_id=request.model_id,
        name=request.model_id,  # Use ID as name if not provided
        context_price=request.context_price,
        generation_price=request.generation_price
    )
    
    if success:
        db.log_action("model_pricing_update", request.actor, 
                     f"Updated model {request.model_id} pricing: context={request.context_price}, generation={request.generation_price}")
        return {
            "status": "success",
            "id": request.model_id,
            "context_price": request.context_price,
            "generation_price": request.generation_price
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update model pricing")

@router.post("/api/credits/groups/update", tags=["credits"])
async def update_group_credits(request: GroupUpdateRequest):
    """Update group default credits"""
    success = db.update_group(
        group_id=request.group_id,
        name=request.name,
        default_credits=request.default_credits
    )
    
    if success:
        db.log_action("group_update", request.actor, 
                     f"Updated group {request.group_id} ({request.name}) default credits to {request.default_credits}")
        return {
            "status": "success",
            "id": request.group_id,
            "name": request.name,
            "default_credits": request.default_credits
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update group")

# Transaction history and logs
@router.get("/api/credits/user/{user_id}/transactions", tags=["credits"])
async def get_user_transaction_history(user_id: str, limit: int = Query(100, ge=1, le=1000)):
    """Get user's transaction history"""
    transactions = db.get_user_transactions(user_id, limit)
    return {"transactions": transactions}

@router.get("/api/credits/transactions", tags=["credits"])
async def get_all_transactions(limit: int = Query(100, ge=1, le=1000)):
    """Get all transactions"""
    transactions = db.get_all_transactions(limit)
    return {"transactions": transactions}

@router.get("/api/credits/system-logs", tags=["credits"])
async def get_system_logs(limit: int = Query(100, ge=1, le=1000)):
    """Get system logs"""
    logs = db.get_logs(limit)
    return {"logs": logs}

# Sync functions
async def sync_user_from_openwebui(user_id: str):
    """Sync a single user from OpenWebUI database"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM user WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user:
                # Create user in credit system with default group
                db.update_user_credits(
                    user_id=user["id"],
                    new_balance=1000.0,  # Default credits
                    actor="sync",
                    transaction_type="sync",
                    reason="Synced from OpenWebUI"
                )
                return True
    except Exception as e:
        print(f"Error syncing user {user_id}: {e}")
    return False

async def sync_all_users_from_openwebui():
    """Sync all users from OpenWebUI database"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM user")
            users = cursor.fetchall()
            
            for user in users:
                existing = db.get_user_credits(user["id"])
                if not existing:
                    db.update_user_credits(
                        user_id=user["id"],
                        new_balance=1000.0,  # Default credits
                        actor="sync",
                        transaction_type="sync",
                        reason="Initial sync from OpenWebUI"
                    )
    except Exception as e:
        print(f"Error syncing users: {e}")


