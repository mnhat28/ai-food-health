from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_
from datetime import datetime
import logging
import google.generativeai as genai
import json
import os

from database.connection import AsyncSessionLocal
from models.user import User
from models.food_log import FoodLog
from services.email_service import send_daily_reminder, send_weekly_report

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ==========================================
# Helper functions
# ==========================================

async def get_users_for_reminder(reminder_hour: int) -> list[User]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.email_reminder == True,
                    User.reminder_time == f"{reminder_hour:02d}:00",
                )
            )
        )
        return result.scalars().all()


async def get_all_active_users() -> list[User]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        return result.scalars().all()


async def generate_ai_weekly_report(user: User) -> str | None:
    try:
        if not GEMINI_API_KEY:
            return None

        async with AsyncSessionLocal() as db:
            from datetime import timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            result = await db.execute(
                select(FoodLog).where(
                    and_(
                        FoodLog.user_id == user.id,
                        FoodLog.eaten_at >= start_date,
                        FoodLog.eaten_at <= end_date,
                    )
                ).order_by(FoodLog.eaten_at)
            )
            logs = result.scalars().all()

            if not logs:
                return None

            from collections import defaultdict
            logs_by_date = defaultdict(list)
            for log in logs:
                logs_by_date[log.eaten_at.date()].append(log)

            weekly_data = [
                {
                    "date": str(d),
                    "calories": round(sum(l.total_calories or 0 for l in day_logs), 1),
                    "protein": round(sum(l.total_protein or 0 for l in day_logs), 1),
                    "carbohydrates": round(sum(l.total_carbohydrates or 0 for l in day_logs), 1),
                    "fat": round(sum(l.total_fat or 0 for l in day_logs), 1),
                    "meals": [l.food_name for l in day_logs],
                }
                for d, day_logs in logs_by_date.items()
            ]

            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                f"""
User profile:
- Calorie goal: {user.calorie_goal or 'Not set'} kcal/day

Weekly food data:
{json.dumps(weekly_data, indent=2)}

Generate a short weekly nutrition summary with 1-2 specific recommendations.
Respond in plain text without markdown formatting, max 4 sentences.
                """.strip(),
                generation_config=genai.GenerationConfig(
                    max_output_tokens=512,
                    temperature=0.7,
                ),
            )
            return response.text

    except Exception as e:
        logger.error(f"[Scheduler] Failed to generate AI report for user {user.id}: {e}")
        return None


# ==========================================
# Job functions
# ==========================================

async def job_daily_reminder(hour: int):
    logger.info(f"[Scheduler] Running daily reminder job for hour {hour:02d}:00")

    users = await get_users_for_reminder(hour)
    if not users:
        logger.info(f"[Scheduler] No users with reminder time {hour:02d}:00")
        return

    success_count = 0
    fail_count = 0

    async with AsyncSessionLocal() as db:
        for user in users:
            try:
                sent = await send_daily_reminder(user, db)
                if sent:
                    success_count += 1
                    logger.info(f"[Scheduler] Daily reminder sent to {user.email}")
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"[Scheduler] Failed to send reminder to {user.email}: {e}")

    logger.info(
        f"[Scheduler] Daily reminder job done — "
        f"success: {success_count}, failed: {fail_count}"
    )


async def job_weekly_report():
    logger.info("[Scheduler] Running weekly report job")

    users = await get_all_active_users()
    if not users:
        logger.info("[Scheduler] No active users found")
        return

    success_count = 0
    fail_count = 0

    for user in users:
        try:
            ai_report = await generate_ai_weekly_report(user)

            async with AsyncSessionLocal() as db:
                sent = await send_weekly_report(user, db, ai_report=ai_report)
                if sent:
                    success_count += 1
                    logger.info(f"[Scheduler] Weekly report sent to {user.email}")
                else:
                    fail_count += 1

        except Exception as e:
            fail_count += 1
            logger.error(f"[Scheduler] Failed to send weekly report to {user.email}: {e}")

    logger.info(
        f"[Scheduler] Weekly report job done — "
        f"success: {success_count}, failed: {fail_count}"
    )


async def job_cleanup_inactive_logs():
    logger.info("[Scheduler] Running cleanup job")
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=365)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FoodLog).where(FoodLog.created_at < cutoff)
        )
        old_logs = result.scalars().all()

        count = len(old_logs)
        for log in old_logs:
            await db.delete(log)
        await db.commit()

    logger.info(f"[Scheduler] Cleanup done — deleted {count} old logs")


# ==========================================
# Scheduler setup
# ==========================================

def setup_scheduler():
    # Daily reminder — run every hour, each job handles users with that reminder_time
    for hour in range(6, 23):
        scheduler.add_job(
            job_daily_reminder,
            trigger=CronTrigger(hour=hour, minute=0),
            args=[hour],
            id=f"daily_reminder_{hour:02d}",
            name=f"Daily Reminder {hour:02d}:00",
            replace_existing=True,
            misfire_grace_time=300,
        )

    # Weekly report — every Sunday at 09:00
    scheduler.add_job(
        job_weekly_report,
        trigger=CronTrigger(day_of_week="sun", hour=9, minute=0),
        id="weekly_report",
        name="Weekly Nutrition Report",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Cleanup old logs — every day at 03:00
    scheduler.add_job(
        job_cleanup_inactive_logs,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_logs",
        name="Cleanup Old Logs",
        replace_existing=True,
        misfire_grace_time=300,
    )

    logger.info("[Scheduler] All jobs registered successfully")
    return scheduler