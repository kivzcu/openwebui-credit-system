import os
import asyncio
import ssl
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

# SSL Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to credit_admin/
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

# Async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_observer
    
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

if __name__ == "__main__":
    import uvicorn
    if ENABLE_SSL:
        print(f"🔒 Starting with SSL enabled")
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
            port=8000, 
            reload=True,
            ssl_certfile=SSL_CERT_PATH,
            ssl_keyfile=SSL_KEY_PATH
        )
    else:
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

