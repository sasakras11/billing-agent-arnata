"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab

from config import get_settings

settings = get_settings()

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    # Sync loads from McLeod every 15 minutes
    "sync-mcleod-loads": {
        "task": "tasks.celery_tasks.sync_mcleod_loads",
        "schedule": crontab(minute=f"*/{settings.mcleod_sync_interval}"),
    },
    
    # Update container statuses every 30 minutes
    "update-container-statuses": {
        "task": "tasks.celery_tasks.update_container_statuses",
        "schedule": crontab(minute="*/30"),
    },
    
    # Check and send alerts every hour
    "check-alerts": {
        "task": "tasks.celery_tasks.check_and_send_alerts",
        "schedule": crontab(minute="0"),  # Top of every hour
    },
    
    # Process pending invoices every 4 hours
    "process-pending-invoices": {
        "task": "tasks.celery_tasks.process_pending_invoices",
        "schedule": crontab(minute="0", hour="*/4"),
    },
    
    # Check payment status daily at 9 AM
    "check-payment-status": {
        "task": "tasks.celery_tasks.check_payment_status",
        "schedule": crontab(hour="9", minute="0"),
    },
    
    # Daily report at 5 PM
    "daily-report": {
        "task": "tasks.celery_tasks.generate_daily_report",
        "schedule": crontab(hour="17", minute="0"),
    },
}


if __name__ == "__main__":
    celery_app.start()

