"""
Initialization script for the refactored credit management system.
Migrates data from JSON to SQLite and sets up the new database.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import db

def main():
    print("🚀 Initializing Credit Management System v2.0")
    print("=" * 50)
    
    try:
        # Initialize database
        print("📊 Setting up database schema...")
        db.init_database()
        print("✅ Database schema created")
        
        # Migration from JSON has been removed; do not attempt automatic migration
        existing_users = db.get_all_users_with_credits()
        if not existing_users:
            print("⚠️  No existing users found in database.")
        else:
            print(f"✅ Found {len(existing_users)} existing users in database")
        
        # Display summary
        users = db.get_all_users_with_credits()
        models = db.get_all_models()
        groups = db.get_all_groups()
        
        print("\n📋 Database Summary:")
        print(f"   👥 Users: {len(users)}")
        print(f"   🤖 Models: {len(models)}")
        print(f"   🏷️  Groups: {len(groups)}")
        
        if models:
            print("\n🔧 Model Pricing:")
            for model in models[:5]:  # Show first 5 models
                print(f"   {model['name']}: {model['context_price']:.4f} (input) / {model['generation_price']:.4f} (output)")
        
        print("\n🎉 Credit Management System v2.0 is ready!")
        print("📡 New optimized API endpoints available:")
        print("   - GET  /api/credits/user/{user_id}")
        print("   - GET  /api/credits/model/{model_id}")
        print("   - POST /api/credits/deduct-tokens")
        print("   - (and more...)")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
