"""Scheduler for periodic email sync and transaction processing."""

from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from backend.config import get_config
from backend.gmail import get_gmail_service
from backend.pipeline.transaction_pipeline import get_transaction_pipeline


class EmailSyncScheduler:
    """Scheduler for periodic email synchronization and transaction processing."""
    
    def __init__(
        self,
        gmail_service=None,
        transaction_pipeline=None,
        scheduler=None,
    ):
        """Initialize the email sync scheduler.
        
        Args:
            gmail_service: GmailService instance. If None, uses global instance.
            transaction_pipeline: TransactionPipeline instance. If None, uses global instance.
            scheduler: APScheduler instance. If None, creates new BackgroundScheduler.
        """
        self.gmail_service = gmail_service or get_gmail_service()
        self.transaction_pipeline = transaction_pipeline or get_transaction_pipeline()
        self.scheduler = scheduler or BackgroundScheduler()
        self.is_running = False
    
    def start(self) -> None:
        """Start the scheduler if not already running."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        config = get_config()
        
        # Add job for periodic email sync
        self.scheduler.add_job(
            self.sync_and_process_emails,
            trigger=IntervalTrigger(minutes=config.gmail.sync_interval_minutes),
            id="email_sync",
            name="Email Sync and Transaction Processing",
            replace_existing=True,
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started with {config.gmail.sync_interval_minutes} minute interval")
    
    def stop(self) -> None:
        """Stop the scheduler if running."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Scheduler stopped")
    
    def sync_and_process_emails(self) -> dict:
        """Sync emails from Gmail and process them into transactions.
        
        This is the main job function called by the scheduler.
        
        Returns:
            Summary dict with processing results.
        """
        logger.info("Starting scheduled email sync")
        
        try:
            config = get_config()
            
            # Fetch emails from Gmail
            emails = self.gmail_service.sync_emails(
                query=config.gmail.search_query,
                max_results=config.gmail.max_results_per_sync,
            )
            
            logger.info(f"Fetched {len(emails)} emails from Gmail")
            
            # Process emails into transactions
            summary = self.transaction_pipeline.process_emails(emails)
            
            logger.info(f"Scheduled sync completed: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error in scheduled email sync: {e}")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "duplicates": 0,
                "error": str(e),
            }
    
    def trigger_manual_sync(self) -> dict:
        """Manually trigger an email sync (useful for testing or immediate sync).
        
        Returns:
            Summary dict with processing results.
        """
        logger.info("Triggering manual email sync")
        return self.sync_and_process_emails()
    
    def get_next_run_time(self) -> Optional[str]:
        """Get the next scheduled run time.
        
        Returns:
            ISO format datetime string of next run, or None if not scheduled.
        """
        if not self.is_running:
            return None
        
        job = self.scheduler.get_job("email_sync")
        if job:
            return job.next_run_time.isoformat()
        return None


# Global scheduler instance
_scheduler: Optional[EmailSyncScheduler] = None


def get_scheduler() -> EmailSyncScheduler:
    """Get the global scheduler instance (singleton pattern)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = EmailSyncScheduler()
    return _scheduler


def reset_scheduler() -> None:
    """Reset the global scheduler (useful for testing)."""
    global _scheduler
    if _scheduler and _scheduler.is_running:
        _scheduler.stop()
    _scheduler = None
