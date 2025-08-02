#!/usr/bin/env python3
"""
Credit Reset Scheduler Service
This service runs as a background process and checks for needed monthly resets.
It should be started on system startup and will run continuously.
"""

import sys
import os
import time
import threading
import signal
from datetime import datetime, timezone, timedelta
import logging

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from app.database import CreditDatabase
except ImportError:
    try:
        from database import CreditDatabase
    except ImportError:
        # Direct import fallback
        sys.path.append(os.path.join(parent_dir, 'app'))
        from database import CreditDatabase

# Configure logging
log_file = '/root/sources/openwebui-credit-system/credit_admin/data/scheduler.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CreditResetScheduler:
    def __init__(self):
        self.db = CreditDatabase()
        self.running = False
        self.thread = None
        self.check_interval = 3600  # Check every hour (in seconds)
        
    def start(self):
        """Start the scheduler service"""
        logger.info("🚀 Starting Credit Reset Scheduler Service")
        logger.info(f"   Check interval: {self.check_interval} seconds ({self.check_interval/3600:.1f} hours)")
        logger.info(f"   Log file: {log_file}")
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("✅ Credit Reset Scheduler Service started successfully")
        
    def stop(self):
        """Stop the scheduler service"""
        logger.info("🛑 Stopping Credit Reset Scheduler Service...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("✅ Credit Reset Scheduler Service stopped")
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("📅 Scheduler loop started")
        
        # Perform initial check on startup
        self._check_and_perform_reset()
        
        while self.running:
            try:
                # Wait for the check interval
                time.sleep(self.check_interval)
                
                if not self.running:
                    break
                    
                # Perform the check
                self._check_and_perform_reset()
                
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
                
        logger.info("📅 Scheduler loop ended")
        
    def _check_and_perform_reset(self):
        """Check if reset is needed and perform it if necessary"""
        try:
            current_time = datetime.now(timezone.utc)
            logger.info(f"🔍 Checking for needed reset at {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Check if monthly reset is needed
            if self.db.needs_monthly_reset():
                logger.info("📊 Monthly reset is needed - performing reset...")
                
                result = self.db.perform_monthly_reset()
                
                if result['success']:
                    logger.info(f"✅ Monthly reset completed successfully!")
                    logger.info(f"   Users affected: {result['users_affected']}")
                    logger.info(f"   Total credits reset: {result['total_credits_reset']:.2f}")
                    logger.info(f"   Reset date: {result['reset_date']}")
                    
                    # Log to system log as well
                    self.db.log_action(
                        log_type="scheduled_reset",
                        actor="scheduler",
                        message=f"Automated monthly reset completed - {result['users_affected']} users affected",
                        metadata=result
                    )
                    
                else:
                    logger.error(f"❌ Monthly reset failed: {result['message']}")
                    if 'error' in result:
                        logger.error(f"   Error details: {result['error']}")
                        
            else:
                logger.info("✅ No reset needed - already performed this month")
                
        except Exception as e:
            error_msg = f"Unexpected error during reset check: {e}"
            logger.error(f"❌ {error_msg}")
            
            # Try to record the error in the database
            try:
                self.db.log_action(
                    log_type="scheduler_error",
                    actor="scheduler", 
                    message=error_msg,
                    metadata={"error": str(e)}
                )
            except:
                pass  # If we can't log to DB, at least we have the file log
                
    def get_status(self):
        """Get the current status of the scheduler"""
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'next_check': time.time() + self.check_interval if self.running else None,
            'log_file': log_file
        }


def main():
    """Main function"""
    scheduler = CreditResetScheduler()
    
    try:
        scheduler.start()
        
        # Keep the main thread alive
        while scheduler.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("📡 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Unexpected error in main: {e}")
    finally:
        scheduler.stop()


if __name__ == '__main__':
    main()
