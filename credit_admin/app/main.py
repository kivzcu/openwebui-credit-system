import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import credits_v2
from app.database import db

# Async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Initializing Credit Management System v2.0...")
    try:
        # Check if migration is needed
        users = db.get_all_users_with_credits()
        if not users:
            print("🔄 Migrating from JSON files...")
            db.migrate_from_json()
        
        # Sync users from OpenWebUI
        await credits_v2.sync_all_users_from_openwebui()
        
        print("✅ Database initialized and ready!")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
    
    yield  # Application runs here
    
    # Shutdown (if needed)
    print("🛑 Shutting down...")

app = FastAPI(lifespan=lifespan)

# Static files setup
static_dir = os.path.join(os.path.dirname(__file__), "static")
index_file = os.path.join(static_dir, "index.html")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    return FileResponse(index_file)

# Include the new optimized credit API
app.include_router(credits_v2.router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

