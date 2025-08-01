"""
Optimized API endpoints for credit management system.
Uses SQLite database instead of JSON files and provides targeted endpoints.
"""

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from typing import Optional, List
import sqlite3
from datetime import datetime, timezone
from pydantic import BaseModel

from app.database import db
from app.config import DB_FILE  # OpenWebUI database for user sync
from app.auth import get_current_admin_user, verify_api_key, User

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
    price_mode: str = "credits"  # "credits" or "usd"
    is_free: bool = False  # whether the model is free
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
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    actor: str = "auto-system"

class SettingsUpdateRequest(BaseModel):
    usd_to_credit_ratio: Optional[float] = None
    token_multiplier: Optional[int] = None
    actor: str = "admin"

# User-specific endpoints (optimized for extensions)
@router.get("/api/credits/user/{user_id}", tags=["credits"])
async def get_user_credits(user_id: str, _: bool = Depends(verify_api_key)):
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

@router.get("/api/credits/model/{model_id:path}", tags=["credits"])
async def get_model_pricing(model_id: str, _: bool = Depends(verify_api_key)):
    """Get specific model's pricing information - optimized for extensions"""
    model_data = db.get_model_pricing(model_id)
    
    if not model_data:
        # Auto-create model with default pricing if not exists
        db.update_model_pricing(model_id, model_id, 0.001, 0.004, True)  # Default to available
        model_data = db.get_model_pricing(model_id)
        db.log_action("model_auto_created", "system", f"Auto-created model {model_id} with default pricing")
        
        if not model_data:  # Still None after creation - something went wrong
            raise HTTPException(status_code=500, detail="Failed to create model pricing")
    
    return {
        "id": model_data["id"],
        "name": model_data["name"],
        "context_price": model_data["context_price"],
        "generation_price": model_data["generation_price"],
        "is_free": model_data.get("is_free", False)
    }

# Optimized credit deduction endpoint for extensions
@router.post("/api/credits/deduct-tokens", tags=["credits"])
async def deduct_credits_for_tokens(request: CreditDeductionRequest, _: bool = Depends(verify_api_key)):
    """
    Optimized endpoint for credit deduction based on token usage.
    Now also accepts cached_tokens and reasoning_tokens for logging.
    """
    # Get user and model data efficiently
    user_data = db.get_user_credits(request.user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    model_data = db.get_model_pricing(request.model_id)
    if not model_data:
        raise HTTPException(status_code=404, detail="Model pricing not found")

    # Check if model is free
    is_free = model_data.get("is_free", False)
    
    if is_free:
        # For free models, no credits are deducted
        total_cost = 0.0
        prompt_cost = 0.0
        completion_cost = 0.0
        deducted = 0.0
        new_balance = user_data["balance"]
        
        # Still log the usage for tracking purposes
        db.log_action("free_model_usage", request.actor, 
                     f"Free model usage: {request.model_id} - {request.prompt_tokens} prompt + {request.completion_tokens} completion tokens")
    else:
        # Calculate cost (only prompt_tokens and completion_tokens count for cost)
        prompt_cost = request.prompt_tokens * model_data["context_price"]
        completion_cost = request.completion_tokens * model_data["generation_price"]
        total_cost = prompt_cost + completion_cost

        # Deduct credits and log all token details
        deducted, new_balance = db.deduct_credits(
            user_id=request.user_id,
            amount=total_cost,
            actor=request.actor,
            reason=(
                f"Token usage: {request.prompt_tokens} prompt + {request.completion_tokens} completion tokens"
                f" (cached_tokens={request.cached_tokens}, reasoning_tokens={request.reasoning_tokens})"
            ),
            model_id=request.model_id,
            prompt_tokens=request.prompt_tokens,
            completion_tokens=request.completion_tokens,
            cached_tokens=request.cached_tokens,
            reasoning_tokens=request.reasoning_tokens
        )

    return {
        "success": True,
        "cost": total_cost,
        "deducted": deducted,
        "new_balance": new_balance,
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost,
        "cached_tokens": request.cached_tokens,
        "reasoning_tokens": request.reasoning_tokens,
        "is_free": is_free
    }

# Batch endpoint for admin UI (when you need multiple users/models)
@router.get("/api/credits/users", tags=["credits"])
async def get_all_users_with_credits(current_user: User = Depends(get_current_admin_user)):
    """Get all users with credit information - for admin UI"""
    # First sync users from OpenWebUI
    await sync_all_users_from_openwebui()
    
    users = db.get_all_users_with_credits()
    
    # Get additional user info from OpenWebUI database using the reusable method
    openwebui_users = db.get_users_info_from_openwebui()
    
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
async def get_all_models(current_user: User = Depends(get_current_admin_user)):
    """Get all model pricing information with availability status - for admin UI"""
    # Get all models from our local database (availability is already stored)
    models = db.get_all_models()
    
    # Get USD conversion ratio for display
    usd_ratio = db.get_usd_to_credit_ratio()
    
    return [
        {
            "id": model["id"],
            "name": model["name"],
            "context_price": model["context_price"],
            "generation_price": model["generation_price"],
            "context_price_usd": db.credits_to_usd(model["context_price"]),
            "generation_price_usd": db.credits_to_usd(model["generation_price"]),
            "is_available": model.get("is_available", True),  # Default to True for backward compatibility
            "is_free": model.get("is_free", False)  # Default to False for backward compatibility
        }
        for model in models
    ]

@router.get("/api/credits/groups", tags=["credits"])
async def get_all_groups(current_user: User = Depends(get_current_admin_user)):
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
async def update_user_credits(request: CreditUpdateRequest, current_user: User = Depends(get_current_admin_user)):
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
async def update_model_pricing(request: ModelPricingRequest, current_user: User = Depends(get_current_admin_user)):
    """Update model pricing (preserves availability status) - supports both USD and credit pricing"""
    # Get current model data to preserve availability status
    current_model = db.get_model_pricing(request.model_id)
    current_availability = current_model.get("is_available", True) if current_model else True
    
    # Convert prices to credits if they're provided in USD
    if request.price_mode == "usd":
        context_price_credits = db.usd_to_credits(request.context_price)
        generation_price_credits = db.usd_to_credits(request.generation_price)
    else:
        context_price_credits = request.context_price
        generation_price_credits = request.generation_price
    
    success = db.update_model_pricing(
        model_id=request.model_id,
        name=request.model_id,  # Use ID as name if not provided
        context_price=context_price_credits,
        generation_price=generation_price_credits,
        is_available=current_availability,  # Preserve current availability status
        is_free=request.is_free  # Update free status
    )
    
    if success:
        db.log_action("model_pricing_update", request.actor, 
                     f"Updated model {request.model_id} pricing: context={context_price_credits}, generation={generation_price_credits}, is_free={request.is_free} (mode: {request.price_mode})")
        return {
            "status": "success",
            "id": request.model_id,
            "context_price": context_price_credits,
            "generation_price": generation_price_credits,
            "context_price_usd": db.credits_to_usd(context_price_credits),
            "generation_price_usd": db.credits_to_usd(generation_price_credits),
            "is_free": request.is_free
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update model pricing")

@router.post("/api/credits/models/update-free-status", tags=["credits"])
async def update_model_free_status(request: dict, current_user: User = Depends(get_current_admin_user)):
    """Update model free status only"""
    model_id = request.get("model_id")
    is_free = request.get("is_free", False)
    actor = request.get("actor", "admin")
    
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")
    
    success = db.update_model_free_status(model_id, is_free)
    
    if success:
        db.log_action("model_free_status_update", actor, 
                     f"Updated model {model_id} free status to {is_free}")
        return {
            "status": "success",
            "model_id": model_id,
            "is_free": is_free
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update model free status")

@router.post("/api/credits/groups/update", tags=["credits"])
async def update_group_credits(request: GroupUpdateRequest, current_user: User = Depends(get_current_admin_user)):
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
async def get_user_transaction_history(user_id: str, limit: int = Query(100, ge=1, le=1000), current_user: User = Depends(get_current_admin_user)):
    """Get user's transaction history with user name - Admin only"""
    transactions = db.get_user_transactions(user_id, limit)
    
    # Get user name once since all transactions belong to the same user
    if transactions:
        users_info = db.get_users_info_from_openwebui([user_id])
        user_info = users_info.get(user_id, {})
        user_name = user_info.get('name') if user_info.get('name') else user_info.get('email')
        
        # Add user name to all transactions
        for transaction in transactions:
            transaction['user_name'] = user_name
    
    return {"transactions": transactions}

@router.get("/api/credits/transactions", tags=["credits"])
async def get_all_transactions(limit: int = Query(100, ge=1, le=1000), current_user: User = Depends(get_current_admin_user)):
    """Get all transactions with user names (optimized) - Admin only"""
    transactions = db.get_all_transactions(limit)
    
    if not transactions:
        return {"transactions": []}
    
    # Get all unique user IDs from transactions
    user_ids = list(set(t['user_id'] for t in transactions))
    
    # Fetch all user names in one query using the reusable method
    users_info = db.get_users_info_from_openwebui(user_ids)
    
    # Add user names to transactions
    for transaction in transactions:
        user_info = users_info.get(transaction['user_id'], {})
        transaction['user_name'] = user_info.get('name') if user_info.get('name') else user_info.get('email')
    
    return {"transactions": transactions}

@router.get("/api/credits/system-logs", tags=["logs"])
async def get_system_logs(limit: int = Query(100, ge=1, le=1000), current_user: User = Depends(get_current_admin_user)):
    """Get system logs"""
    logs = db.get_logs(limit)
    return {"logs": logs}

# Public endpoint for model pricing
@router.get("/api/public/models/pricing", tags=["public"])
async def get_public_model_pricing():
    """Get pricing for only available models - public endpoint (no authentication required)"""
    # Get all models from our local database and filter by availability
    all_models = db.get_all_models()
    
    # Filter to only include models that are available (stored locally)
    available_models = [
        {
            "id": model["id"],
            "name": model["name"],
            "context_price": model["context_price"],
            "generation_price": model["generation_price"],
            "is_free": model.get("is_free", False)
        }
        for model in all_models
        if model.get("is_available", True)  # Default to True for backward compatibility
    ]
    
    return available_models

# Settings endpoints
@router.get("/api/credits/settings", tags=["settings"])
async def get_settings(current_user: User = Depends(get_current_admin_user)):
    """Get system settings - Admin only"""
    return {
        "usd_to_credit_ratio": db.get_usd_to_credit_ratio(),
        "token_multiplier": db.get_token_multiplier()
    }

@router.post("/api/credits/settings", tags=["settings"])
async def update_settings(request: SettingsUpdateRequest, current_user: User = Depends(get_current_admin_user)):
    """Update system settings - Admin only"""
    updated_fields = []
    
    if request.usd_to_credit_ratio is not None:
        success = db.set_usd_to_credit_ratio(request.usd_to_credit_ratio)
        if success:
            updated_fields.append(f"USD to credit ratio: {request.usd_to_credit_ratio}")
        else:
            raise HTTPException(status_code=500, detail="Failed to update USD to credit ratio")
    
    if request.token_multiplier is not None:
        success = db.set_token_multiplier(request.token_multiplier)
        if success:
            updated_fields.append(f"Token multiplier: {request.token_multiplier}")
        else:
            raise HTTPException(status_code=500, detail="Failed to update token multiplier")
    
    if updated_fields:
        return {
            "status": "success",
            "message": f"Updated: {', '.join(updated_fields)}",
            "usd_to_credit_ratio": db.get_usd_to_credit_ratio(),
            "token_multiplier": db.get_token_multiplier()
        }
    else:
        raise HTTPException(status_code=400, detail="No valid settings provided")

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

async def sync_models_from_openwebui():
    """Sync all models from OpenWebUI database with availability status"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, base_model_id, is_active FROM model")
            models = cursor.fetchall()
            
            # Get current available model IDs from OpenWebUI
            available_model_ids = set()
            for model in models:
                if model["is_active"]:
                    available_model_ids.add(model["id"])
            
            # Get all models from our local database
            local_models = db.get_all_models()
            local_model_ids = {model["id"] for model in local_models}
            
            synced_count = 0
            updated_count = 0
            
            # Update availability for all models
            for model in models:
                model_id = model["id"]
                model_name = model["name"] or model_id
                is_available = bool(model["is_active"])
                
                if model_id in local_model_ids:
                    # Update existing model availability
                    if db.update_model_availability(model_id, is_available):
                        updated_count += 1
                else:
                    # Create new model with availability status
                    success = db.update_model_pricing(
                        model_id=model_id,
                        name=model_name,
                        context_price=0.001,  # Default context price
                        generation_price=0.004,  # Default generation price
                        is_available=is_available
                    )
                    if success:
                        synced_count += 1
                        db.log_action("model_sync", "sync", f"Auto-synced model {model_id} from OpenWebUI (available: {is_available})")
            
            # Mark models as unavailable if they no longer exist in OpenWebUI
            openwebui_model_ids = {model["id"] for model in models}
            for local_model in local_models:
                if local_model["id"] not in openwebui_model_ids:
                    if db.update_model_availability(local_model["id"], False):
                        updated_count += 1
            
            if synced_count > 0 or updated_count > 0:
                print(f"✅ Model sync: {synced_count} new, {updated_count} updated")
            return synced_count + updated_count
    except Exception as e:
        print(f"Error syncing models: {e}")
        return 0

async def sync_all_users_from_openwebui():
    """Sync all users from OpenWebUI database"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM user")
            users = cursor.fetchall()
            
            synced_count = 0
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
                    synced_count += 1
            
            if synced_count > 0:
                print(f"✅ Synced {synced_count} new users from OpenWebUI")
            return synced_count
    except Exception as e:
        print(f"Error syncing users: {e}")
        return 0

async def sync_all_from_openwebui():
    """Sync both users and models from OpenWebUI database"""
    user_count = await sync_all_users_from_openwebui()
    model_count = await sync_models_from_openwebui()
    return {"users": user_count, "models": model_count}

# Manual sync endpoint
@router.post("/api/credits/sync-users", tags=["admin"])
async def manual_sync_users(current_user: User = Depends(get_current_admin_user)):
    """Manually trigger user sync from OpenWebUI database"""
    try:
        count = await sync_all_users_from_openwebui()
        db.log_action("manual_sync", "admin", f"Manual user sync triggered - synced {count} users")
        return {"status": "success", "message": f"Synced {count} users successfully"}
    except Exception as e:
        return {"status": "error", "message": f"User sync failed: {str(e)}"}

@router.post("/api/credits/sync-models", tags=["admin"])
async def manual_sync_models(current_user: User = Depends(get_current_admin_user)):
    """Manually trigger model sync from OpenWebUI database"""
    try:
        count = await sync_models_from_openwebui()
        db.log_action("manual_sync", "admin", f"Manual model sync triggered - synced {count} models")
        return {"status": "success", "message": f"Synced {count} models successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Model sync failed: {str(e)}"}

@router.post("/api/credits/sync-all", tags=["admin"])
async def manual_sync_all(current_user: User = Depends(get_current_admin_user)):
    """Manually trigger full sync of users and models from OpenWebUI database"""
    try:
        result = await sync_all_from_openwebui()
        total = result["users"] + result["models"]
        db.log_action("manual_sync", "admin", f"Manual full sync triggered - synced {result['users']} users and {result['models']} models")
        return {
            "status": "success", 
            "message": f"Synced {result['users']} users and {result['models']} models successfully",
            "details": result
        }
    except Exception as e:
        return {"status": "error", "message": f"Full sync failed: {str(e)}"}


