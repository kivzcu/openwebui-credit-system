import os
import asyncio
import ssl
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.api import credits_v2, auth
from app.database import db
from app.config import DB_FILE
from app.auth import print_security_config

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to credit_admin/
PORT = int(os.getenv("PORT", "8000"))

# SSL Configuration
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", os.path.join(BASE_DIR, "ssl", "cert.pem"))
SSL_KEY_PATH = os.getenv("SSL_KEY_PATH", os.path.join(BASE_DIR, "ssl", "key.pem"))
ENABLE_SSL = os.getenv("ENABLE_SSL", "false").lower() == "true"

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

# Configure logging for reset operations
reset_logger = logging.getLogger('credit_reset')
reset_logger.setLevel(logging.INFO)
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
    global db_observer, reset_task
    
    # Startup
    print("🚀 Initializing Credit Management System v2.0...")
    
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
        
        # Start watching OpenWebUI database for changes
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
    
    # Stop database watcher
    if db_observer:
        print("🛑 Stopping database watcher...")
        db_observer.stop()
        db_observer.join()

app = FastAPI(lifespan=lifespan)

# Static files setup
static_dir = os.path.join(os.path.dirname(__file__), "static")
index_file = os.path.join(static_dir, "index.html")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    return FileResponse(index_file)

@app.get("/pricing")
def serve_pricing():
    """Public pricing page - no authentication required"""
    pricing_file = os.path.join(static_dir, "pricing.html")
    return FileResponse(pricing_file)

# Include routers
app.include_router(auth.router)
app.include_router(credits_v2.router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (public)
@app.get("/health", tags=["health"])
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
    import uvicorn
    if ENABLE_SSL:
        print(f"🔒 Starting with SSL enabled on port {PORT}")
        print(f"📄 SSL Certificate: {SSL_CERT_PATH}")
        print(f"🔑 SSL Key: {SSL_KEY_PATH}")
        
        # Verify SSL files exist
        if not os.path.exists(SSL_CERT_PATH):
            print(f"❌ SSL certificate not found: {SSL_CERT_PATH}")
            exit(1)
        if not os.path.exists(SSL_KEY_PATH):
            print(f"❌ SSL key not found: {SSL_KEY_PATH}")
            exit(1)
            
        uvicorn.run(
            "app.main:app", 
            host="0.0.0.0", 
            port=PORT, 
            reload=True,
            ssl_certfile=SSL_CERT_PATH,
            ssl_keyfile=SSL_KEY_PATH
        )
    else:
        print(f"🌐 Starting on port {PORT}")
        uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)

