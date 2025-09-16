from dotenv import load_dotenv
import os
import argparse
import sys


# Load environment variables from .env file in credit_admin/
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

import asyncio
import ssl
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.api import credits_v2, auth
from app.database import db
from app.config import BASE_DIR, DB_FILE, DATABASE_URL, CREDIT_DATABASE_URL
from app.auth import print_security_config
import uvicorn

def is_postgresql_database():
    """Check if we're using PostgreSQL database instead of SQLite"""
    from app.config import CREDIT_DATABASE_URL
    try:
        import psycopg2
        return bool(CREDIT_DATABASE_URL)
    except ImportError:
        return False

def obfuscate_db_url(url: str) -> str:
    """Obfuscate password in database URL for logging"""
    if not url:
        return url
    
    # Handle PostgreSQL URLs like: postgresql://user:password@host:port/db
    if url.startswith('postgresql://'):
        # Find the password part between : and @
        colon_pos = url.find(':', 14)  # After postgresql://
        at_pos = url.find('@', colon_pos)
        if colon_pos != -1 and at_pos != -1:
            return url[:colon_pos+1] + '***' + url[at_pos:]
    
    # Handle SQLite paths - no obfuscation needed
    return url

# Configuration

ENABLE_SSL = False

def get_uvicorn_config():
    parser = argparse.ArgumentParser(description="Run the Credit Management System")
    parser.add_argument('--host', default=os.getenv('HOST', '0.0.0.0'), help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8001')), help='Port to bind (default: 8001)')
    parser.add_argument('--reload', action='store_true', default=os.getenv('RELOAD', 'true').lower() == 'true', help='Enable auto-reload (default: true in dev)')
    parser.add_argument('--ssl-certfile', help='Path to SSL certificate file')
    parser.add_argument('--ssl-keyfile', help='Path to SSL key file')
    args = parser.parse_args()

    # Load SSL paths from env if not provided via args
    ENABLE_SSL = os.getenv("ENABLE_SSL", "false").lower() == "true"
    if ENABLE_SSL and not args.ssl_certfile:
        args.ssl_certfile = os.getenv("SSL_CERT_PATH", os.path.join(BASE_DIR, "ssl", "cert.pem"))
    if ENABLE_SSL and not args.ssl_keyfile:
        args.ssl_keyfile = os.getenv("SSL_KEY_PATH", os.path.join(BASE_DIR, "ssl", "key.pem"))

    config = {
        'host': args.host,
        'port': args.port,
        'reload': args.reload,
    }

    if args.ssl_certfile:
        if not os.path.exists(args.ssl_certfile):
            print(f"❌ SSL certificate not found: {args.ssl_certfile}")
            sys.exit(1)
        if not args.ssl_keyfile or not os.path.exists(args.ssl_keyfile):
            print(f"❌ SSL key not found: {args.ssl_keyfile}")
            sys.exit(1)
        config['ssl_certfile'] = args.ssl_certfile
        config['ssl_keyfile'] = args.ssl_keyfile
        print(f"🔒 Starting with SSL enabled on port {args.port}")
        print(f"📄 SSL Certificate: {args.ssl_certfile}")
        print(f"🔑 SSL Key: {args.ssl_keyfile}")
    else:
        print(f"🌐 Starting on port {args.port}")

    return config





# Security Middleware
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clean dangerous query params and redirect if found
        dangerous = {'username', 'password', 'user', 'pass', 'login', 'auth', 'token'}
        query = request.query_params.multi_items()
        cleaned = [(k, v) for (k, v) in query if k.lower() not in dangerous]
        
        if len(cleaned) != len(query):
            # Build clean URL and redirect (302)
            from urllib.parse import urlencode
            clean_qs = urlencode(cleaned, doseq=True)
            clean_url = str(request.url.replace(query=clean_qs))
            
            # Log security incident before redirect
            client_ip = request.client.host if request.client else "unknown"
            try:
                db.log_action(
                    log_type="security_warning",
                    actor="security_middleware",
                    message=f"Credentials in URL. Redirecting to clean URL. From IP {client_ip}: {request.url.path}",
                    metadata={"client_ip": client_ip, "user_agent": request.headers.get("user-agent", "unknown")}
                )
            except Exception as e:
                print(f"Failed to log security warning: {e}")
                
            print(f"🚨 SECURITY: Redirecting credentials in URL from {client_ip} to clean URL")
            return Response(status_code=302, headers={"Location": clean_url})
        
        # Continue processing if URL is clean
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add Strict-Transport-Security for HTTPS
        if ENABLE_SSL:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

# File watcher for OpenWebUI database changes
class OpenWebUIDBWatcher(FileSystemEventHandler):
    def __init__(self, loop):
        self.last_modified = 0
        self.loop = loop  # Store reference to the main event loop
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if event.src_path == DB_FILE:
            # Debounce - only sync if more than 2 seconds since last modification
            import time
            current_time = time.time()
            if current_time - self.last_modified > 2:
                self.last_modified = current_time
                print(f"🔄 OpenWebUI database changed, syncing users and models...")
                # Schedule the coroutine to run in the main event loop
                asyncio.run_coroutine_threadsafe(
                    credits_v2.sync_all_from_openwebui(), 
                    self.loop
                )

# Global observer instance
db_observer = None
reset_task = None  # Global background task for reset checking
sync_task = None  # Global background task for OpenWebUI sync (PostgreSQL only)

# Configure logging for reset operations
reset_logger = logging.getLogger('credit_reset')
reset_logger.setLevel(logging.INFO)

# Only add handler if none exist (prevents duplicate handlers on reload)
if not reset_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [RESET] %(message)s'))
    reset_logger.addHandler(handler)

async def periodic_reset_checker():
    """Background task that periodically checks for needed monthly resets"""
    reset_logger.info("🔄 Starting periodic credit reset checker...")
    
    while True:
        try:
            # Check every hour (3600 seconds)
            await asyncio.sleep(3600)
            
            reset_logger.info("🔍 Checking if monthly reset is needed...")
            
            if db.needs_monthly_reset():
                reset_logger.info("📊 Monthly reset is needed - performing reset...")
                
                result = db.perform_monthly_reset()
                
                if result['success']:
                    reset_logger.info(f"✅ Monthly reset completed successfully!")
                    reset_logger.info(f"   Users affected: {result['users_affected']}")
                    reset_logger.info(f"   Total credits reset: {result['total_credits_reset']:.2f}")
                    reset_logger.info(f"   Reset date: {result['reset_date']}")
                    
                    # Log to system log as well
                    db.log_action(
                        log_type="scheduled_reset",
                        actor="background_task",
                        message=f"Automated monthly reset completed - {result['users_affected']} users affected",
                        metadata=result
                    )
                    
                else:
                    reset_logger.error(f"❌ Monthly reset failed: {result['message']}")
                    if 'error' in result:
                        reset_logger.error(f"   Error details: {result['error']}")
                        
            else:
                reset_logger.info("✅ No reset needed - already performed this month")
                
        except asyncio.CancelledError:
            reset_logger.info("🛑 Periodic reset checker cancelled")
            break
        except Exception as e:
            reset_logger.error(f"❌ Error in periodic reset checker: {e}")
            # Log error to database if possible
            try:
                db.log_action(
                    log_type="reset_checker_error",
                    actor="background_task",
                    message=f"Error in periodic reset checker: {str(e)}",
                    metadata={"error": str(e)}
                )
            except:
                pass  # If we can't log to DB, at least we have the console log

async def periodic_openwebui_sync():
    """Background task that periodically syncs users, models, and groups from OpenWebUI (for PostgreSQL)"""
    sync_logger = logging.getLogger('openwebui_sync')
    sync_logger.setLevel(logging.INFO)

    # Only add handler if none exist (prevents duplicate handlers on reload)
    if not sync_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [SYNC] %(message)s'))
        sync_logger.addHandler(handler)

    sync_logger.info("🔄 Starting periodic OpenWebUI sync...")

    while True:
        try:
            # Sync every 5 minutes (300 seconds)
            await asyncio.sleep(300)

            sync_logger.info("🔍 Syncing users, models, and groups from OpenWebUI...")

            result = await credits_v2.sync_all_from_openwebui()

            if result['users'] > 0 or result['models'] > 0 or result['groups'] > 0:
                sync_logger.info(f"✅ Sync completed - Users: {result['users']}, Models: {result['models']}, Groups: {result['groups']}, User-Groups: {result['user_groups']}")
            else:
                sync_logger.info("✅ Sync completed - No changes detected")

        except asyncio.CancelledError:
            sync_logger.info("🛑 Periodic OpenWebUI sync cancelled")
            break
        except Exception as e:
            sync_logger.error(f"❌ Error in periodic OpenWebUI sync: {e}")
            # Log error to database if possible
            try:
                db.log_action(
                    log_type="sync_error",
                    actor="background_task",
                    message=f"Error in periodic OpenWebUI sync: {str(e)}",
                    metadata={"error": str(e)}
                )
            except:
                pass  # If we can't log to DB, at least we have the console log

async def check_reset_on_startup():
    """Check for needed reset immediately on startup"""
    try:
        reset_logger.info("🚀 Performing startup reset check...")
        
        if db.needs_monthly_reset():
            reset_logger.info("📊 Monthly reset needed on startup - performing reset...")
            
            result = db.perform_monthly_reset()
            
            if result['success']:
                reset_logger.info(f"✅ Startup reset completed successfully!")
                reset_logger.info(f"   Users affected: {result['users_affected']}")
                reset_logger.info(f"   Total credits reset: {result['total_credits_reset']:.2f}")
                
                db.log_action(
                    log_type="startup_reset",
                    actor="startup_task",
                    message=f"Startup reset completed - {result['users_affected']} users affected",
                    metadata=result
                )
            else:
                reset_logger.error(f"❌ Startup reset failed: {result['message']}")
        else:
            reset_logger.info("✅ No reset needed on startup")
            
    except Exception as e:
        reset_logger.error(f"❌ Error during startup reset check: {e}")


# Async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_observer, reset_task, sync_task
    
    # Startup
    print("🚀 Initializing Credit Management System v2.0...")
    
    # Print database configuration
    if DATABASE_URL:
        print(f"🔗 OPENWEBUI DB: PostgreSQL ({obfuscate_db_url(DATABASE_URL)})")
    elif DB_FILE:
        print(f"🔗 OPENWEBUI DB: SQLite ({DB_FILE})")
    else:
        print("🔗 OPENWEBUI DB: Not configured")
    
    if is_postgresql_database():
        print(f"💾 CREDIT ADMIN DB: PostgreSQL ({obfuscate_db_url(CREDIT_DATABASE_URL)})")
    else:
        print("💾 CREDIT ADMIN DB: SQLite")
    
    # Print security configuration
    print_security_config()
    
    try:
        # Check if migration is needed
        users = db.get_all_users_with_credits()
        if not users:
            print("🔄 Migrating from JSON files...")
            db.migrate_from_json()
        
        # Sync users and models from OpenWebUI
        await credits_v2.sync_all_from_openwebui()
        
        # Perform initial reset check
        await check_reset_on_startup()
        
        # Start periodic reset checker as background task
        reset_task = asyncio.create_task(periodic_reset_checker())
        print("🔄 Started periodic reset checker (checks every hour)")
        
        # Choose sync method based on OpenWebUI database type
        if DATABASE_URL:
            # PostgreSQL: Use periodic sync instead of file watching
            print("🔄 Using PostgreSQL for OpenWebUI - starting periodic sync (every 5 minutes)")
            sync_task = asyncio.create_task(periodic_openwebui_sync())
        else:
            # SQLite: Use file watching
            if os.path.exists(DB_FILE):
                print(f"👁️  Watching OpenWebUI database: {DB_FILE}")
                # Get the current event loop
                loop = asyncio.get_running_loop()
                event_handler = OpenWebUIDBWatcher(loop)
                db_observer = Observer()
                db_observer.schedule(event_handler, os.path.dirname(DB_FILE), recursive=False)
                db_observer.start()
            else:
                print(f"⚠️  OpenWebUI database not found: {DB_FILE}")
        
        print("✅ Database initialized and ready!")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
    
    yield  # Application runs here
    
    # Shutdown
    print("🛑 Shutting down...")
    
    # Cancel the reset checker task
    if reset_task:
        print("🛑 Stopping periodic reset checker...")
        reset_task.cancel()
        try:
            await reset_task
        except asyncio.CancelledError:
            pass
    
    # Cancel the sync task (PostgreSQL only)
    if sync_task:
        print("🛑 Stopping periodic OpenWebUI sync...")
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    
    # Stop database watcher
    if db_observer:
        print("🛑 Stopping database watcher...")
        db_observer.stop()
        db_observer.join()

app = FastAPI(lifespan=lifespan)

# Add security middleware first
app.add_middleware(SecurityMiddleware)

# Static files setup
static_dir = os.path.join(os.path.dirname(__file__), "static")
index_file = os.path.join(static_dir, "index.html")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
@app.head("/")
def serve_index():
    return FileResponse(index_file)

@app.get("/pricing")
@app.head("/pricing")
def serve_pricing():
    """Public pricing page - no authentication required"""
    pricing_file = os.path.join(static_dir, "pricing.html")
    return FileResponse(pricing_file)

# Include routers
app.include_router(auth.router)
app.include_router(credits_v2.router)

# CORS middleware - Tighten for production security
# In production, replace "*" with actual allowed origins like ["https://yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: In production, specify exact origins like ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrict to needed methods only
    allow_headers=["*"],
)

# Health check endpoint (public)
@app.get("/health", tags=["health"])
@app.head("/health", tags=["health"])
async def health_check():
    """Public health check endpoint for monitoring"""
    return {"status": "healthy", "service": "credit-management-system", "version": "2.0"}

# Reset status and manual trigger endpoints
@app.get("/api/reset/status", tags=["reset"])
async def get_reset_status():
    """Get the current reset status and history"""
    try:
        # Get reset history
        history = db.get_reset_history(10)
        
        # Check if reset is needed
        needs_reset = db.needs_monthly_reset()
        
        # Get last reset info
        last_reset_date = db.get_last_reset_date('monthly')
        
        return {
            "needs_reset": needs_reset,
            "last_reset_date": last_reset_date,
            "reset_history": history,
            "checker_status": "running" if reset_task and not reset_task.done() else "stopped"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/reset/manual", tags=["reset"])
async def manual_reset():
    """Manually trigger a monthly reset"""
    try:
        reset_logger.info("🔧 Manual reset triggered via API")
        
        result = db.perform_monthly_reset()
        
        if result['success']:
            reset_logger.info(f"✅ Manual reset completed successfully!")
            db.log_action(
                log_type="manual_reset",
                actor="api_user",
                message=f"Manual reset completed - {result['users_affected']} users affected",
                metadata=result
            )
        
        return result
    except Exception as e:
        error_msg = f"Error during manual reset: {str(e)}"
        reset_logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
            "users_affected": 0,
            "total_credits_reset": 0.0,
            "error": str(e)
        }

if __name__ == "__main__":
    config = get_uvicorn_config()
    uvicorn.run("app.main:app", **config)
