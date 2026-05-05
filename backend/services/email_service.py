from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Subject, HtmlContent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, extract
from datetime import datetime, timedelta
from typing import Optional
import os

from models.user import User
from models.food_log import FoodLog


SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "AI Food Health")
APP_NAME = os.getenv("NEXT_PUBLIC_APP_NAME", "AI Food Health")


# ==========================================
# HTML Templates
# ==========================================

def build_daily_reminder_html(
    username: str,
    total_calories: float,
    calorie_goal: Optional[float],
    meals_logged: int,
    protein: float,
    carbohydrates: float,
    fat: float,
) -> str:
    goal_percentage = 0
    goal_color = "#22c55e"
    goal_text = "No calorie goal set"

    if calorie_goal and calorie_goal > 0:
        goal_percentage = min(round(total_calories / calorie_goal * 100), 100)
        goal_text = f"{round(total_calories)} / {round(calorie_goal)} kcal ({goal_percentage}%)"
        if goal_percentage < 50:
            goal_color = "#f97316"
        elif goal_percentage < 80:
            goal_color = "#eab308"
        else:
            goal_color = "#22c55e"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Nutrition Summary</title>
</head>
<body style="margin:0; padding:0; background:#f8fafc; font-family: -apple-system, sans-serif;">
    <div style="max-width:560px; margin:32px auto; background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <div style="background:linear-gradient(135deg, #16a34a, #15803d); padding:32px 40px;">
            <h1 style="margin:0; color:#ffffff; font-size:24px; font-weight:700;">
                {APP_NAME}
            </h1>
            <p style="margin:8px 0 0; color:#bbf7d0; font-size:14px;">
                Daily Nutrition Summary — {datetime.now().strftime("%B %d, %Y")}
            </p>
        </div>

        <!-- Greeting -->
        <div style="padding:32px 40px 0;">
            <p style="margin:0; color:#374151; font-size:16px;">
                Hi <strong>{username}</strong> 👋
            </p>
            <p style="margin:8px 0 0; color:#6b7280; font-size:14px;">
                Here is your nutrition summary for today.
                You logged <strong>{meals_logged} meal{"s" if meals_logged != 1 else ""}</strong> today.
            </p>
        </div>

        <!-- Calorie Progress -->
        <div style="padding:24px 40px 0;">
            <p style="margin:0 0 8px; color:#374151; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
                Calorie Progress
            </p>
            <p style="margin:0 0 8px; color:{goal_color}; font-size:22px; font-weight:700;">
                {goal_text}
            </p>
            <div style="background:#f1f5f9; border-radius:999px; height:10px; overflow:hidden;">
                <div style="background:{goal_color}; width:{goal_percentage}%; height:100%; border-radius:999px; transition:width 0.3s;"></div>
            </div>
        </div>

        <!-- Macros -->
        <div style="padding:24px 40px 0; display:flex; gap:16px;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td width="33%" style="text-align:center; padding:16px; background:#f0fdf4; border-radius:12px;">
                        <p style="margin:0; color:#16a34a; font-size:20px; font-weight:700;">{round(protein)}g</p>
                        <p style="margin:4px 0 0; color:#6b7280; font-size:12px;">Protein</p>
                    </td>
                    <td width="4%"></td>
                    <td width="33%" style="text-align:center; padding:16px; background:#eff6ff; border-radius:12px;">
                        <p style="margin:0; color:#2563eb; font-size:20px; font-weight:700;">{round(carbohydrates)}g</p>
                        <p style="margin:4px 0 0; color:#6b7280; font-size:12px;">Carbs</p>
                    </td>
                    <td width="4%"></td>
                    <td width="33%" style="text-align:center; padding:16px; background:#fefce8; border-radius:12px;">
                        <p style="margin:0; color:#ca8a04; font-size:20px; font-weight:700;">{round(fat)}g</p>
                        <p style="margin:4px 0 0; color:#6b7280; font-size:12px;">Fat</p>
                    </td>
                </tr>
            </table>
        </div>

        <!-- CTA -->
        <div style="padding:32px 40px;">
            <a href="{os.getenv('NEXT_PUBLIC_APP_URL', 'http://localhost:3000')}/dashboard"
               style="display:block; text-align:center; background:#16a34a; color:#ffffff;
                      text-decoration:none; padding:14px 24px; border-radius:10px;
                      font-size:15px; font-weight:600;">
                View Full Dashboard
            </a>
        </div>

        <!-- Footer -->
        <div style="padding:0 40px 32px;">
            <p style="margin:0; color:#9ca3af; font-size:12px; text-align:center;">
                You are receiving this email because you enabled daily reminders in {APP_NAME}.<br>
                <a href="{os.getenv('NEXT_PUBLIC_APP_URL', 'http://localhost:3000')}/settings"
                   style="color:#6b7280;">Unsubscribe</a>
            </p>
        </div>

    </div>
</body>
</html>
    """.strip()


def build_weekly_report_html(
    username: str,
    avg_calories: float,
    calorie_goal: Optional[float],
    avg_protein: float,
    avg_carbohydrates: float,
    avg_fat: float,
    days_logged: int,
    ai_report: Optional[str] = None,
) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Nutrition Report</title>
</head>
<body style="margin:0; padding:0; background:#f8fafc; font-family:-apple-system, sans-serif;">
    <div style="max-width:560px; margin:32px auto; background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <div style="background:linear-gradient(135deg, #7c3aed, #6d28d9); padding:32px 40px;">
            <h1 style="margin:0; color:#ffffff; font-size:24px; font-weight:700;">
                Weekly Report
            </h1>
            <p style="margin:8px 0 0; color:#ddd6fe; font-size:14px;">
                {(datetime.now() - timedelta(days=7)).strftime("%B %d")} — {datetime.now().strftime("%B %d, %Y")}
            </p>
        </div>

        <!-- Greeting -->
        <div style="padding:32px 40px 0;">
            <p style="margin:0; color:#374151; font-size:16px;">
                Hi <strong>{username}</strong> 👋
            </p>
            <p style="margin:8px 0 0; color:#6b7280; font-size:14px;">
                You logged meals on <strong>{days_logged} out of 7 days</strong> this week.
                Here is your weekly nutrition overview.
            </p>
        </div>

        <!-- Weekly Averages -->
        <div style="padding:24px 40px 0;">
            <p style="margin:0 0 16px; color:#374151; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
                Weekly Averages (per day)
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="padding:12px 16px; background:#f8fafc; border-radius:8px 8px 0 0; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#6b7280; font-size:14px;">Avg Calories</span>
                        <span style="float:right; color:#374151; font-weight:600;">{round(avg_calories)} kcal
                            {f'/ {round(calorie_goal)} goal' if calorie_goal else ''}
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="padding:12px 16px; background:#f8fafc; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#6b7280; font-size:14px;">Avg Protein</span>
                        <span style="float:right; color:#16a34a; font-weight:600;">{round(avg_protein)}g</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding:12px 16px; background:#f8fafc; border-bottom:1px solid #e2e8f0;">
                        <span style="color:#6b7280; font-size:14px;">Avg Carbohydrates</span>
                        <span style="float:right; color:#2563eb; font-weight:600;">{round(avg_carbohydrates)}g</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding:12px 16px; background:#f8fafc; border-radius:0 0 8px 8px;">
                        <span style="color:#6b7280; font-size:14px;">Avg Fat</span>
                        <span style="float:right; color:#ca8a04; font-weight:600;">{round(avg_fat)}g</span>
                    </td>
                </tr>
            </table>
        </div>

        <!-- AI Report -->
        {f'''
        <div style="padding:24px 40px 0;">
            <p style="margin:0 0 12px; color:#374151; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
                AI Nutrition Insights
            </p>
            <div style="background:#faf5ff; border-left:4px solid #7c3aed; border-radius:0 8px 8px 0; padding:16px;">
                <p style="margin:0; color:#374151; font-size:14px; line-height:1.6;">
                    {ai_report}
                </p>
            </div>
        </div>
        ''' if ai_report else ''}

        <!-- CTA -->
        <div style="padding:32px 40px;">
            <a href="{os.getenv('NEXT_PUBLIC_APP_URL', 'http://localhost:3000')}/dashboard"
               style="display:block; text-align:center; background:#7c3aed; color:#ffffff;
                      text-decoration:none; padding:14px 24px; border-radius:10px;
                      font-size:15px; font-weight:600;">
                View Full Report
            </a>
        </div>

        <!-- Footer -->
        <div style="padding:0 40px 32px;">
            <p style="margin:0; color:#9ca3af; font-size:12px; text-align:center;">
                You are receiving this email because you enabled weekly reports in {APP_NAME}.<br>
                <a href="{os.getenv('NEXT_PUBLIC_APP_URL', 'http://localhost:3000')}/settings"
                   style="color:#6b7280;">Unsubscribe</a>
            </p>
        </div>

    </div>
</body>
</html>
    """.strip()


# ==========================================
# Email sending functions
# ==========================================

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    try:
        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=(EMAIL_FROM, EMAIL_FROM_NAME),
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )
        response = sg.send(message)
        return response.status_code in [200, 201, 202]
    except Exception as e:
        print(f"[EmailService] Failed to send email to {to_email}: {e}")
        return False


async def send_daily_reminder(user: User, db: AsyncSession) -> bool:
    if not user.email_reminder or not user.is_active:
        return False

    # Get today's food logs
    today = datetime.now()
    result = await db.execute(
        select(FoodLog).where(
            and_(
                FoodLog.user_id == user.id,
                extract("year", FoodLog.eaten_at) == today.year,
                extract("month", FoodLog.eaten_at) == today.month,
                extract("day", FoodLog.eaten_at) == today.day,
            )
        )
    )
    logs = result.scalars().all()

    total_calories = sum(log.total_calories or 0 for log in logs)
    total_protein = sum(log.total_protein or 0 for log in logs)
    total_carbs = sum(log.total_carbohydrates or 0 for log in logs)
    total_fat = sum(log.total_fat or 0 for log in logs)

    html = build_daily_reminder_html(
        username=user.full_name or user.username,
        total_calories=total_calories,
        calorie_goal=user.calorie_goal,
        meals_logged=len(logs),
        protein=total_protein,
        carbohydrates=total_carbs,
        fat=total_fat,
    )

    return send_email(
        to_email=user.email,
        subject=f"[{APP_NAME}] Your Daily Nutrition Summary",
        html_content=html,
    )


async def send_weekly_report(
    user: User,
    db: AsyncSession,
    ai_report: Optional[str] = None,
) -> bool:
    if not user.is_active:
        return False

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    result = await db.execute(
        select(FoodLog).where(
            and_(
                FoodLog.user_id == user.id,
                FoodLog.eaten_at >= start_date,
                FoodLog.eaten_at <= end_date,
            )
        )
    )
    logs = result.scalars().all()

    if not logs:
        return False

    from collections import defaultdict
    logs_by_date = defaultdict(list)
    for log in logs:
        logs_by_date[log.eaten_at.date()].append(log)

    days_logged = len(logs_by_date)
    avg_calories = sum(log.total_calories or 0 for log in logs) / 7
    avg_protein = sum(log.total_protein or 0 for log in logs) / 7
    avg_carbs = sum(log.total_carbohydrates or 0 for log in logs) / 7
    avg_fat = sum(log.total_fat or 0 for log in logs) / 7

    html = build_weekly_report_html(
        username=user.full_name or user.username,
        avg_calories=avg_calories,
        calorie_goal=user.calorie_goal,
        avg_protein=avg_protein,
        avg_carbohydrates=avg_carbs,
        avg_fat=avg_fat,
        days_logged=days_logged,
        ai_report=ai_report,
    )

    return send_email(
        to_email=user.email,
        subject=f"[{APP_NAME}] Your Weekly Nutrition Report",
        html_content=html,
    )