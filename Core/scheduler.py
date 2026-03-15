from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db.models import update_all_users_progress

_scheduler = None


def start_scheduler():
    """
    Start a background scheduler that updates all users' daily stats every 30 minutes.

    Safe to call multiple times; only the first call creates the scheduler.
    """
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    # Run every 30 minutes to keep platform stats fresh
    scheduler.add_job(
        update_all_users_progress,
        IntervalTrigger(minutes=30),
        id="platform_progress",
        replace_existing=True,
    )
    scheduler.start()

    _scheduler = scheduler
    return scheduler

