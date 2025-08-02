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
            
            # Add is_free column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE credit_models ADD COLUMN is_free BOOLEAN NOT NULL DEFAULT 0")
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
            
            # Initialize default token multiplier (1K tokens)
            cursor.execute("""
                INSERT OR IGNORE INTO credit_settings (key, value) 
                VALUES ('token_multiplier', '1000')
            """)
            
            # Reset tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_reset_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reset_type TEXT NOT NULL,  -- 'monthly', 'manual', etc.
                    reset_date DATE NOT NULL,  -- YYYY-MM-DD format
                    reset_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    users_affected INTEGER NOT NULL DEFAULT 0,
                    total_credits_reset REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL DEFAULT 'completed',  -- 'pending', 'completed', 'failed'
                    error_message TEXT,
                    metadata TEXT  -- JSON string for additional data
                )
            """)
            
            # Monthly usage statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_usage_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,  -- 1-12
                    credits_used REAL NOT NULL DEFAULT 0.0,
                    transactions_count INTEGER NOT NULL DEFAULT 0,
                    models_used TEXT,  -- JSON array of model IDs used
                    balance_before_reset REAL,  -- Balance at end of month, before next reset
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, year, month)
                )
            """)
            
            # Add balance_before_reset column if it doesn't exist (migration)
            try:
                cursor.execute("ALTER TABLE credit_usage_statistics ADD COLUMN balance_before_reset REAL")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_credit_users_group ON credit_users(group_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON credit_transactions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_model ON credit_transactions(model_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_type ON credit_logs(log_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reset_tracking_date ON credit_reset_tracking(reset_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reset_tracking_type ON credit_reset_tracking(reset_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_stats_user ON credit_usage_statistics(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_stats_date ON credit_usage_statistics(year, month)")
            
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
                      prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None,
                      cached_tokens: Optional[int] = None, reasoning_tokens: Optional[int] = None) -> tuple[float, float]:
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
                (user_id, amount, transaction_type, reason, actor, balance_after, model_id, prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, -deducted, "deduct", reason, actor, new_balance, model_id, prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens))
            conn.commit()
            
            # Update usage statistics (only if credits were actually deducted)
            if deducted > 0:
                self.update_usage_statistics(user_id, deducted, model_id)
            
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

    def update_model_free_status(self, model_id: str, is_free: bool) -> bool:
        """Update model free status only"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE credit_models SET is_free = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (is_free, model_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_model_pricing(self, model_id: str, name: str, context_price: float, 
                           generation_price: float, is_available: bool = True, is_free: bool = False) -> bool:
        """Update model pricing, availability status, and free status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO credit_models (id, name, context_price, generation_price, is_available, is_free, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (model_id, name, context_price, generation_price, is_available, is_free))
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
    
    def delete_log_entry(self, log_id: int) -> bool:
        """Delete a specific log entry by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credit_logs WHERE id = ?", (log_id,))
            conn.commit()
            return cursor.rowcount > 0

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
            print(f"Error getting monthly usage summary: {e}")
            return None
    
    def get_yearly_usage_summary(self, year):
        """Get yearly usage summary for a given year"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(credits_used), 0) as total_credits_used,
                        COALESCE(SUM(transactions_count), 0) as total_transactions,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) as total_entries
                    FROM credit_usage_statistics 
                    WHERE year = ?
                """, (year,))
                
                result = cursor.fetchone()
                if result and result["total_entries"] > 0:
                    # Count unique models
                    cursor.execute("""
                        SELECT models_used 
                        FROM credit_usage_statistics 
                        WHERE year = ? AND models_used IS NOT NULL
                    """, (year,))
                    
                    all_models = set()
                    for row in cursor.fetchall():
                        try:
                            models = json.loads(row["models_used"])
                            all_models.update(models)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    summary = dict(result)
                    summary["unique_models"] = len(all_models)
                    return summary
                
                return None
        except Exception as e:
            print(f"Error getting yearly usage summary: {e}")
            return None
    
    def insert_dummy_statistics(self, user_id, year, month, credits_used, transactions_count, models_used, balance_before_reset=None):
        """Insert dummy statistics data for testing"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if entry already exists
                cursor.execute("""
                    SELECT id FROM credit_usage_statistics 
                    WHERE user_id = ? AND year = ? AND month = ?
                """, (user_id, year, month))
                
                if cursor.fetchone():
                    # Update existing entry
                    cursor.execute("""
                        UPDATE credit_usage_statistics 
                        SET credits_used = ?, transactions_count = ?, models_used = ?, balance_before_reset = ?
                        WHERE user_id = ? AND year = ? AND month = ?
                    """, (credits_used, transactions_count, json.dumps(models_used), balance_before_reset, user_id, year, month))
                else:
                    # Insert new entry
                    cursor.execute("""
                        INSERT INTO credit_usage_statistics 
                        (user_id, year, month, credits_used, transactions_count, models_used, balance_before_reset)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, year, month, credits_used, transactions_count, json.dumps(models_used), balance_before_reset))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error inserting dummy statistics: {e}")
            return False
    
    def update_july_balance_before_reset(self):
        """Update July 2025 statistics with calculated balance_before_reset values"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all July 2025 statistics entries
                cursor.execute("""
                    SELECT user_id, credits_used FROM credit_usage_statistics
                    WHERE year = 2025 AND month = 7
                """)
                july_stats = cursor.fetchall()
                
                updated_count = 0
                
                for user_id, credits_used in july_stats:
                    # For dummy data, we'll assume they started with 900 credits (default group)
                    # and calculate what their balance would have been at end of July
                    starting_balance = 900.0  # Default credits for most users
                    balance_before_reset = max(0, starting_balance - credits_used)
                    
                    # Update the record
                    cursor.execute("""
                        UPDATE credit_usage_statistics 
                        SET balance_before_reset = ?
                        WHERE user_id = ? AND year = 2025 AND month = 7
                    """, (balance_before_reset, user_id))
                    
                    updated_count += 1
                    print(f"Updated {user_id}: used {credits_used:.2f}, balance before reset: {balance_before_reset:.2f}")
                
                conn.commit()
                print(f"\n✅ Updated {updated_count} July 2025 records with balance_before_reset")
                return True
                
        except Exception as e:
            print(f"❌ Error updating July balance_before_reset: {e}")
            return False

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

    def get_token_multiplier(self) -> int:
        """Get the current token multiplier setting"""
        multiplier_str = self.get_setting('token_multiplier', '1000')
        try:
            return int(multiplier_str) if multiplier_str else 1000
        except (ValueError, TypeError):
            return 1000  # Default fallback

    def set_token_multiplier(self, multiplier: int) -> bool:
        """Set the token multiplier setting"""
        return self.set_setting('token_multiplier', str(multiplier))

    # Reset tracking methods
    def record_reset_event(self, reset_type: str, reset_date: str, users_affected: int, 
                          total_credits_reset: float, status: str = 'completed', 
                          error_message: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Record a credit reset event"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO credit_reset_tracking 
                (reset_type, reset_date, users_affected, total_credits_reset, status, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                reset_type, 
                reset_date, 
                users_affected, 
                total_credits_reset, 
                status, 
                error_message,
                json.dumps(metadata) if metadata else None
            ))
            reset_id = cursor.lastrowid
            conn.commit()
            
            # Also log the event
            self.log_action(
                log_type="reset_event",
                actor="system",
                message=f"Credit reset {reset_type} for {users_affected} users on {reset_date}",
                metadata={"reset_id": reset_id, "total_credits": total_credits_reset}
            )
            
            return reset_id or 0  # Ensure we return an int

    def get_last_reset_date(self, reset_type: str = 'monthly') -> Optional[str]:
        """Get the date of the last successful reset of the specified type"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT reset_date FROM credit_reset_tracking 
                WHERE reset_type = ? AND status = 'completed'
                ORDER BY reset_date DESC LIMIT 1
            """, (reset_type,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_reset_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the history of credit resets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM credit_reset_tracking 
                ORDER BY reset_timestamp DESC LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metadata']:
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except json.JSONDecodeError:
                        result['metadata'] = {}
                results.append(result)
            return results

    def needs_monthly_reset(self) -> bool:
        """Check if a monthly reset is needed"""
        from datetime import datetime, timezone
        
        current_date = datetime.now(timezone.utc)
        current_month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        last_reset_date = self.get_last_reset_date('monthly')
        
        if last_reset_date is None:
            return True  # No reset recorded yet
            
        # Parse the last reset date
        try:
            # Parse the date string and make it timezone-aware
            last_reset = datetime.strptime(last_reset_date, '%Y-%m-%d')
            # Make timezone-aware for comparison
            last_reset = last_reset.replace(tzinfo=timezone.utc)
            last_reset_month_start = last_reset.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # If the last reset was in a previous month, we need a new reset
            return last_reset_month_start < current_month_start
        except ValueError:
            return True  # If we can't parse the date, assume we need a reset

    def perform_monthly_reset(self) -> Dict[str, Any]:
        """Perform monthly credit reset for all users"""
        from datetime import datetime, timezone
        
        current_date = datetime.now(timezone.utc)
        reset_date = current_date.strftime('%Y-%m-%d')
        
        # Check if reset is needed
        if not self.needs_monthly_reset():
            return {
                'success': False,
                'message': 'Monthly reset not needed - already performed this month',
                'users_affected': 0,
                'total_credits_reset': 0.0
            }
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all users with their group default credits
                cursor.execute("""
                    SELECT u.id, u.balance, u.group_id, g.default_credits
                    FROM credit_users u
                    LEFT JOIN credit_groups g ON u.group_id = g.id
                    WHERE g.default_credits IS NOT NULL
                """)
                
                users_to_reset = cursor.fetchall()
                users_affected = 0
                total_credits_reset = 0.0
                
                # Store pre-reset balances for previous month statistics
                previous_month = current_date.month - 1
                previous_year = current_date.year
                if previous_month <= 0:
                    previous_month = 12
                    previous_year -= 1
                
                for user in users_to_reset:
                    user_id = user[0]
                    current_balance = user[1]
                    group_id = user[2]
                    default_credits = user[3]
                    
                    # Update previous month's statistics with final balance before reset
                    cursor.execute("""
                        UPDATE credit_usage_statistics 
                        SET balance_before_reset = ?
                        WHERE user_id = ? AND year = ? AND month = ?
                    """, (current_balance, user_id, previous_year, previous_month))
                    
                    if default_credits > 0:
                        # Update user balance
                        cursor.execute("""
                            UPDATE credit_users 
                            SET balance = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (default_credits, user_id))
                        
                        # Record transaction
                        cursor.execute("""
                            INSERT INTO credit_transactions 
                            (user_id, amount, transaction_type, reason, actor, balance_after)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            user_id,
                            default_credits - current_balance,
                            'monthly_reset',
                            f'Monthly reset for group {group_id}',
                            'system',
                            default_credits
                        ))
                        
                        users_affected += 1
                        total_credits_reset += default_credits
                
                conn.commit()
                
                # Initialize monthly statistics for the new month
                self.initialize_monthly_statistics_for_reset(current_date.year, current_date.month)
                
                # Record the reset event
                reset_id = self.record_reset_event(
                    reset_type='monthly',
                    reset_date=reset_date,
                    users_affected=users_affected,
                    total_credits_reset=total_credits_reset,
                    status='completed',
                    metadata={'reset_timestamp': current_date.isoformat()}
                )
                
                return {
                    'success': True,
                    'message': f'Monthly reset completed for {users_affected} users',
                    'users_affected': users_affected,
                    'total_credits_reset': total_credits_reset,
                    'reset_id': reset_id,
                    'reset_date': reset_date
                }
                
        except Exception as e:
            # Record the failed reset attempt
            self.record_reset_event(
                reset_type='monthly',
                reset_date=reset_date,
                users_affected=0,
                total_credits_reset=0.0,
                status='failed',
                error_message=str(e)
            )
            
            return {
                'success': False,
                'message': f'Monthly reset failed: {str(e)}',
                'users_affected': 0,
                'total_credits_reset': 0.0,
                'error': str(e)
            }

    # Usage statistics methods
    def update_usage_statistics(self, user_id: str, amount: float, model_id: Optional[str] = None):
        """Update monthly usage statistics when credits are deducted"""
        from datetime import datetime, timezone
        
        current_date = datetime.now(timezone.utc)
        year = current_date.year
        month = current_date.month
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current statistics for this user and month
                cursor.execute("""
                    SELECT credits_used, transactions_count, models_used 
                    FROM credit_usage_statistics 
                    WHERE user_id = ? AND year = ? AND month = ?
                """, (user_id, year, month))
                
                row = cursor.fetchone()
                
                if row:
                    # Update existing record
                    current_credits = row[0]
                    current_transactions = row[1]
                    models_used_json = row[2] or '[]'
                    
                    try:
                        models_used = json.loads(models_used_json)
                    except json.JSONDecodeError:
                        models_used = []
                    
                    # Add model to list if not already present
                    if model_id and model_id not in models_used:
                        models_used.append(model_id)
                    
                    cursor.execute("""
                        UPDATE credit_usage_statistics 
                        SET credits_used = ?, transactions_count = ?, models_used = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND year = ? AND month = ?
                    """, (
                        current_credits + amount,
                        current_transactions + 1,
                        json.dumps(models_used),
                        user_id, year, month
                    ))
                else:
                    # Create new record
                    models_used = [model_id] if model_id else []
                    cursor.execute("""
                        INSERT INTO credit_usage_statistics 
                        (user_id, year, month, credits_used, transactions_count, models_used)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, year, month, amount, 1, json.dumps(models_used)))
                
                conn.commit()
                
        except Exception as e:
            # Log error but don't fail the main transaction
            self.log_action(
                log_type="statistics_error",
                actor="system",
                message=f"Failed to update usage statistics for user {user_id}: {str(e)}",
                metadata={"user_id": user_id, "amount": amount, "model_id": model_id}
            )

    def get_user_usage_statistics(self, user_id: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Get user's monthly usage statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM credit_usage_statistics 
                WHERE user_id = ? 
                ORDER BY year DESC, month DESC 
                LIMIT ?
            """, (user_id, limit))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['models_used']:
                    try:
                        result['models_used'] = json.loads(result['models_used'])
                    except json.JSONDecodeError:
                        result['models_used'] = []
                else:
                    result['models_used'] = []
                results.append(result)
            return results

    def get_all_usage_statistics(self, year: Optional[int] = None, month: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get usage statistics for all users, optionally filtered by year/month"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if year and month:
                cursor.execute("""
                    SELECT u.*, cu.balance as current_balance, cg.name as group_name
                    FROM credit_usage_statistics u
                    LEFT JOIN credit_users cu ON u.user_id = cu.id
                    LEFT JOIN credit_groups cg ON cu.group_id = cg.id
                    WHERE u.year = ? AND u.month = ?
                    ORDER BY u.credits_used DESC
                    LIMIT ?
                """, (year, month, limit))
            elif year:
                cursor.execute("""
                    SELECT u.*, cu.balance as current_balance, cg.name as group_name
                    FROM credit_usage_statistics u
                    LEFT JOIN credit_users cu ON u.user_id = cu.id
                    LEFT JOIN credit_groups cg ON cu.group_id = cg.id
                    WHERE u.year = ?
                    ORDER BY u.year DESC, u.month DESC, u.credits_used DESC
                    LIMIT ?
                """, (year, limit))
            else:
                cursor.execute("""
                    SELECT u.*, cu.balance as current_balance, cg.name as group_name
                    FROM credit_usage_statistics u
                    LEFT JOIN credit_users cu ON u.user_id = cu.id
                    LEFT JOIN credit_groups cg ON cu.group_id = cg.id
                    ORDER BY u.year DESC, u.month DESC, u.credits_used DESC
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['models_used']:
                    try:
                        result['models_used'] = json.loads(result['models_used'])
                    except json.JSONDecodeError:
                        result['models_used'] = []
                else:
                    result['models_used'] = []
                results.append(result)
            return results

    def get_current_month_pending_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current month's usage for a user (pending/in-progress)"""
        from datetime import datetime, timezone
        
        current_date = datetime.now(timezone.utc)
        year = current_date.year
        month = current_date.month
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM credit_usage_statistics 
                WHERE user_id = ? AND year = ? AND month = ?
            """, (user_id, year, month))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result['models_used']:
                    try:
                        result['models_used'] = json.loads(result['models_used'])
                    except json.JSONDecodeError:
                        result['models_used'] = []
                else:
                    result['models_used'] = []
                return result
            else:
                return {
                    'user_id': user_id,
                    'year': year,
                    'month': month,
                    'credits_used': 0.0,
                    'transactions_count': 0,
                    'models_used': []
                }

    def get_monthly_usage_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get summary statistics for a specific month"""
        from datetime import datetime, timezone
        
        if not year or not month:
            current_date = datetime.now(timezone.utc)
            year = year or current_date.year
            month = month or current_date.month
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get aggregated statistics
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(credits_used), 0) as total_credits_used,
                        COALESCE(SUM(transactions_count), 0) as total_transactions,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) as total_entries
                    FROM credit_usage_statistics 
                    WHERE year = ? AND month = ?
                """, (year, month))
                
                result = cursor.fetchone()
                if result and result["total_entries"] > 0:
                    # Count unique models
                    cursor.execute("""
                        SELECT models_used 
                        FROM credit_usage_statistics 
                        WHERE year = ? AND month = ? AND models_used IS NOT NULL
                    """, (year, month))
                    
                    all_models = set()
                    for row in cursor.fetchall():
                        try:
                            models = json.loads(row["models_used"])
                            all_models.update(models)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    summary = dict(result)
                    summary["unique_models"] = len(all_models)
                    return summary
                
                return None
        except Exception as e:
            print(f"Error getting monthly usage summary: {e}")
            return None

    def initialize_monthly_statistics_for_reset(self, year: int, month: int):
        """Initialize statistics for all users when a new month starts (called during reset)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all users
                cursor.execute("SELECT id FROM credit_users")
                users = cursor.fetchall()
                
                created_count = 0
                for user in users:
                    user_id = user[0]
                    
                    # Check if record already exists
                    cursor.execute("""
                        SELECT id FROM credit_usage_statistics 
                        WHERE user_id = ? AND year = ? AND month = ?
                    """, (user_id, year, month))
                    
                    if not cursor.fetchone():
                        # Create new record with zero usage
                        cursor.execute("""
                            INSERT INTO credit_usage_statistics 
                            (user_id, year, month, credits_used, transactions_count, models_used)
                            VALUES (?, ?, ?, 0.0, 0, '[]')
                        """, (user_id, year, month))
                        created_count += 1
                
                conn.commit()
                
                self.log_action(
                    log_type="statistics_initialization",
                    actor="system",
                    message=f"Initialized monthly statistics for {created_count} users for {year}-{month:02d}",
                    metadata={"year": year, "month": month, "users_initialized": created_count}
                )
                
        except Exception as e:
            self.log_action(
                log_type="statistics_error",
                actor="system",
                message=f"Failed to initialize monthly statistics: {str(e)}",
                metadata={"year": year, "month": month, "error": str(e)}
            )

# Global database instance
db = CreditDatabase()
