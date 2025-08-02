#!/usr/bin/env python3
"""
Enhanced monthly credit reset script with database tracking.
This script replaces the old JSON-based reset system with proper database tracking.
"""

import sys
import os
from datetime import datetime, timezone
import logging

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from app.database import db
except ImportError:
    from database import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/sources/openwebui-credit-system/credit_admin/data/reset.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_reset_needed():
    """Check if a monthly reset is needed"""
    try:
        is_needed = db.needs_monthly_reset()
        logger.info(f"Monthly reset needed: {is_needed}")
        return is_needed
    except Exception as e:
        logger.error(f"Error checking if reset is needed: {e}")
        return False


def perform_reset():
    """Perform the monthly credit reset"""
    logger.info("Starting monthly credit reset...")
    
    try:
        result = db.perform_monthly_reset()
        
        if result['success']:
            logger.info(f"✅ Monthly reset completed successfully!")
            logger.info(f"   Users affected: {result['users_affected']}")
            logger.info(f"   Total credits reset: {result['total_credits_reset']:.2f}")
            logger.info(f"   Reset date: {result['reset_date']}")
            logger.info(f"   Reset ID: {result['reset_id']}")
            
            print(f"Monthly reset completed successfully!")
            print(f"Users affected: {result['users_affected']}")
            print(f"Total credits reset: {result['total_credits_reset']:.2f}")
            
        else:
            logger.error(f"❌ Monthly reset failed: {result['message']}")
            if 'error' in result:
                logger.error(f"   Error details: {result['error']}")
            
            print(f"Monthly reset failed: {result['message']}")
            
        return result
        
    except Exception as e:
        error_msg = f"Unexpected error during monthly reset: {e}"
        logger.error(f"❌ {error_msg}")
        print(error_msg)
        return {
            'success': False,
            'message': error_msg,
            'users_affected': 0,
            'total_credits_reset': 0.0,
            'error': str(e)
        }


def get_reset_history(limit=10):
    """Get the history of recent resets"""
    try:
        history = db.get_reset_history(limit)
        return history
    except Exception as e:
        logger.error(f"Error getting reset history: {e}")
        return []


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Monthly Credit Reset Script - Database Version")
    logger.info("=" * 60)
    
    # Check if reset is needed
    if not check_reset_needed():
        logger.info("Monthly reset not needed - already performed this month")
        print("Monthly reset not needed - already performed this month")
        return
    
    # Perform the reset
    result = perform_reset()
    
    # Show recent reset history
    logger.info("\nRecent reset history:")
    history = get_reset_history(5)
    for reset in history:
        status_emoji = "✅" if reset['status'] == 'completed' else "❌"
        logger.info(f"  {status_emoji} {reset['reset_date']} - {reset['reset_type']} - "
                   f"{reset['users_affected']} users - {reset['total_credits_reset']:.2f} credits")
    
    logger.info("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()
