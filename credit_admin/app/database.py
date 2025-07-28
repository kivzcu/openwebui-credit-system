"""
Database module for credit management system.
Handles SQLite database operations for credits, models, groups, and transactions.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from app.config import CREDITS_FILE, MODELS_FILE, GROUPS_FILE, DB_FILE

# Ne    # ...existing code...path (separate from OpenWebUI)
CREDITS_DB_PATH = "/root/sources/openwebui-credit-system/credit_admin/data/credits.db"

class CreditDatabase:
    def __init__(self, db_path: str = CREDITS_DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table - credits and group assignments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_users (
                    id TEXT PRIMARY KEY,
                    balance REAL NOT NULL DEFAULT 0.0,
                    group_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Groups table - credit groups with default allocations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    default_credits REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Models table - pricing information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    context_price REAL NOT NULL DEFAULT 0.001,  -- cost per input token
                    generation_price REAL NOT NULL DEFAULT 0.004,  -- cost per output token
                    is_available BOOLEAN NOT NULL DEFAULT 1,  -- availability in OpenWebUI
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add is_available column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE credit_models ADD COLUMN is_available BOOLEAN NOT NULL DEFAULT 1")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Transaction history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    transaction_type TEXT NOT NULL,  -- 'deduct', 'add', 'reset', etc.
                    reason TEXT,
                    actor TEXT,  -- who performed the action
                    balance_after REAL NOT NULL,
                    model_id TEXT,  -- optional, for model-specific charges
                    prompt_tokens INTEGER,  -- optional, for token tracking
                    completion_tokens INTEGER,  -- optional, for token tracking
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    message TEXT,
                    metadata TEXT,  -- JSON string for additional data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Settings table for configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize default USD to credit conversion ratio
            cursor.execute("""
                INSERT OR IGNORE INTO credit_settings (key, value) 
                VALUES ('usd_to_credit_ratio', '1000.0')
            """)
            
            # Indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_users_group ON credit_users(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON credit_transactions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_model ON credit_transactions(model_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_type ON credit_logs(log_type)")
            
            conn.commit()
    
    def migrate_from_json(self):
        """Migrate existing JSON data to SQLite"""
        print("🔄 Migrating data from JSON files to SQLite...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Migrate groups
            if os.path.exists(GROUPS_FILE):
                with open(GROUPS_FILE, 'r') as f:
                    groups_data = json.load(f)
                
                for group_id, group_info in groups_data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO credit_groups (id, name, default_credits)
                        VALUES (?, ?, ?)
                    """, (group_id, group_info.get('name', ''), group_info.get('default_credits', 0.0)))
                print(f"✅ Migrated {len(groups_data)} groups")
            
            # Migrate models
            if os.path.exists(MODELS_FILE):
                with open(MODELS_FILE, 'r') as f:
                    models_data = json.load(f)
                
                for model_id, model_info in models_data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO credit_models (id, name, context_price, generation_price)
                        VALUES (?, ?, ?, ?)
                    """, (
                        model_id, 
                        model_info.get('name', model_id),
                        model_info.get('cost_per_token', 0.001),
                        model_info.get('cost_per_second', 0.004)
                    ))
                print(f"✅ Migrated {len(models_data)} models")
            
            # Migrate users and their credit history
            if os.path.exists(CREDITS_FILE):
                with open(CREDITS_FILE, 'r') as f:
                    credits_data = json.load(f)
                
                users = credits_data.get('users', {})
                for user_id, user_info in users.items():
                    # Insert user
                    cursor.execute("""
                        INSERT OR REPLACE INTO credit_users (id, balance, group_id)
                        VALUES (?, ?, ?)
                    """, (user_id, user_info.get('balance', 0.0), user_info.get('group')))
                    
                    # Migrate transaction history
                    history = user_info.get('history', [])
                    for transaction in history:
                        cursor.execute("""
                            INSERT INTO credit_transactions 
                            (user_id, amount, transaction_type, reason, actor, balance_after, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            transaction.get('amount', 0.0),
                            transaction.get('action', 'unknown'),
                            transaction.get('reason', ''),
                            'migration',
                            user_info.get('balance', 0.0),  # We don't have historical balance
                            transaction.get('timestamp', datetime.now(timezone.utc).isoformat())
                        ))
                
                print(f"✅ Migrated {len(users)} users and their transaction history")
            
            conn.commit()
        
        print("🎉 Migration completed successfully!")
    
    # User operations
    def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's credit information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cu.*, cg.name as group_name, cg.default_credits
                FROM credit_users cu
                LEFT JOIN credit_groups cg ON cu.group_id = cg.id
                WHERE cu.id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_users_with_credits(self) -> List[Dict[str, Any]]:
        """Get all users with their credit information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cu.*, cg.name as group_name, cg.default_credits
                FROM credit_users cu
                LEFT JOIN credit_groups cg ON cu.group_id = cg.id
                ORDER BY cu.id
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_user_credits(self, user_id: str, new_balance: float, actor: str = "system", 
                           transaction_type: str = "update", reason: str = "") -> bool:
        """Update user's credit balance"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update balance
            cursor.execute("""
                INSERT OR REPLACE INTO credit_users (id, balance, group_id, updated_at)
                VALUES (?, ?, COALESCE((SELECT group_id FROM credit_users WHERE id = ?), 'default'), CURRENT_TIMESTAMP)
            """, (user_id, new_balance, user_id))
            
            # Log transaction
            cursor.execute("""
                INSERT INTO credit_transactions 
                (user_id, amount, transaction_type, reason, actor, balance_after)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, new_balance, transaction_type, reason, actor, new_balance))
            
            conn.commit()
            return True
    
    def deduct_credits(self, user_id: str, amount: float, actor: str = "system",
                      reason: str = "", model_id: Optional[str] = None, 
                      prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None) -> tuple[float, float]:
        """Deduct credits from user and return (deducted_amount, new_balance)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current balance
            cursor.execute("SELECT balance FROM credit_users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            current_balance = row['balance'] if row else 0.0
            
            # Calculate actual deduction
            deducted = min(current_balance, amount)
            new_balance = max(0.0, current_balance - amount)
            
            # Update balance
            cursor.execute("""
                UPDATE credit_users SET balance = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (new_balance, user_id))
            
            # Log transaction
            cursor.execute("""
                INSERT INTO credit_transactions 
                (user_id, amount, transaction_type, reason, actor, balance_after, model_id, prompt_tokens, completion_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, -deducted, "deduct", reason, actor, new_balance, model_id, prompt_tokens, completion_tokens))
            
            conn.commit()
            return deducted, new_balance
    
    # Model operations
    def get_model_pricing(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model pricing information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM credit_models WHERE id = ?", (model_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get all model pricing information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM credit_models ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_model_availability(self, model_id: str, is_available: bool) -> bool:
        """Update model availability status only"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE credit_models SET is_available = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (is_available, model_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_model_pricing(self, model_id: str, name: str, context_price: float, 
                           generation_price: float, is_available: bool = True) -> bool:
        """Update model pricing and availability status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO credit_models (id, name, context_price, generation_price, is_available, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (model_id, name, context_price, generation_price, is_available))
            conn.commit()
            return True
    
    # Group operations
    def get_all_groups(self) -> List[Dict[str, Any]]:
        """Get all credit groups"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM credit_groups ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_group(self, group_id: str, name: str, default_credits: float) -> bool:
        """Update group information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO credit_groups (id, name, default_credits, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (group_id, name, default_credits))
            conn.commit()
            return True
    
    # Transaction history
    def get_user_transactions(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user's transaction history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ct.*
                FROM credit_transactions ct
                WHERE ct.user_id = ? 
                ORDER BY ct.created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_transactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all transactions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ct.*
                FROM credit_transactions ct
                ORDER BY ct.created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Logging
    def log_action(self, log_type: str, actor: str, message: str, metadata: Optional[Dict] = None):
        """Log system action"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO credit_logs (log_type, actor, message, metadata)
                VALUES (?, ?, ?, ?)
            """, (log_type, actor, message, json.dumps(metadata) if metadata else None))
            conn.commit()
    
    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get system logs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM credit_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_user_name_from_openwebui(self, user_id: str) -> Optional[str]:
        """Get user name from OpenWebUI database"""
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name, email FROM user WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row['name'] if row['name'] else row['email']
            return None
        except Exception as e:
            print(f"Error fetching user name from OpenWebUI: {e}")
            return None

    def get_users_info_from_openwebui(self, user_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
        """
        Get user information from OpenWebUI database.
        If user_ids is None, gets all users. Otherwise gets specific users.
        Returns dict with user_id as key and dict with name/email as value.
        """
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user_ids is None:
                # Get all users
                cursor.execute("SELECT id, name, email FROM user")
            else:
                # Get specific users
                placeholders = ','.join('?' * len(user_ids))
                cursor.execute(f"SELECT id, name, email FROM user WHERE id IN ({placeholders})", user_ids)
            
            result = {}
            for row in cursor.fetchall():
                result[row["id"]] = {
                    "name": row["name"],
                    "email": row["email"]
                }
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"Error fetching user info from OpenWebUI: {e}")
            return {}
    
    def get_setting(self, key: str, default_value: Optional[str] = None) -> Optional[str]:
        """Get a setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM credit_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row['value'] if row else default_value
        except Exception as e:
            print(f"Error getting setting {key}: {e}")
            return default_value
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO credit_settings (key, value, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False
    
    def get_usd_to_credit_ratio(self) -> float:
        """Get the current USD to credit conversion ratio"""
        ratio_str = self.get_setting('usd_to_credit_ratio', '1000.0')
        try:
            return float(ratio_str) if ratio_str else 1000.0
        except (ValueError, TypeError):
            return 1000.0  # Default fallback
    
    def set_usd_to_credit_ratio(self, ratio: float) -> bool:
        """Set the USD to credit conversion ratio"""
        return self.set_setting('usd_to_credit_ratio', str(ratio))
    
    def credits_to_usd(self, credits: float) -> float:
        """Convert credits to USD"""
        ratio = self.get_usd_to_credit_ratio()
        return credits / ratio
    
    def usd_to_credits(self, usd: float) -> float:
        """Convert USD to credits"""
        ratio = self.get_usd_to_credit_ratio()
        return usd * ratio

# Global database instance
db = CreditDatabase()
