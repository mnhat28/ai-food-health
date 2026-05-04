from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, extract
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from typing import Optional, AsyncGenerator
import anthropic
import json
import os

from database.connection import get_db
from models.food_log import FoodLog
from models.user import User
from routers.auth import get_current_user

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

router = APIRouter()


# ==========================================
# Pydantic Schemas
# ==========================================

class AdviceRequest(BaseModel):
    message: str
    date_range: Optional[int] = 7           # number of days to include in context


class AdviceResponse(BaseModel):
    advice: str
    based_on_days: int
    generated_at: datetime


class NutritionContext(BaseModel):
    date: date
    total_calories: float
    total_protein: float
    total_carbohydrates: float
    total_fat: float
    meals: list[dict]


# ==========================================
# Helper functions
# ==========================================

async def get_nutrition_context(
    user_id: str,
    days: int,
    db: AsyncSession,
) -> list[NutritionContext]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    result = await db.execute(
        select(FoodLog).where(
            and_(
                FoodLog.user_id == user_id,
                FoodLog.eaten_at >= start_date,
                FoodLog.eaten_at <= end_date,
            )
        ).order_by(FoodLog.eaten_at)
    )
    logs = result.scalars().all()

    from collections import defaultdict
    logs_by_date = defaultdict(list)
    for log in logs:
        logs_by_date[log.eaten_at.date()].append(log)

    contexts = []
    for i in range(days):
        current_date = (end_date - timedelta(days=days - 1 - i)).date()
        day_logs = logs_by_date.get(current_date, [])

        meals = [
            {
                "meal_type": log.meal_type,
                "food_name": log.food_name,
                "calories": log.total_calories,
                "protein": log.total_protein,
                "carbohydrates": log.total_carbohydrates,
                "fat": log.total_fat,
                "serving_size": log.serving_size,
            }
            for log in day_logs
        ]

        contexts.append(NutritionContext(
            date=current_date,
            total_calories=round(sum(log.total_calories or 0 for log in day_logs), 1),
            total_protein=round(sum(log.total_protein or 0 for log in day_logs), 1),
            total_carbohydrates=round(sum(log.total_carbohydrates or 0 for log in day_logs), 1),
            total_fat=round(sum(log.total_fat or 0 for log in day_logs), 1),
            meals=meals,
        ))

    return contexts


def build_system_prompt(user: User) -> str:
    profile_info = f"""
You are a professional nutrition advisor AI assistant.
Your role is to analyze the user's eating history and provide personalized, 
actionable nutrition advice based on their goals and current habits.

User Profile:
- Name: {user.full_name or user.username}
- Age: {user.age or "Not provided"}
- Gender: {user.gender or "Not provided"}
- Height: {user.height_cm or "Not provided"} cm
- Weight: {user.weight_kg or "Not provided"} kg
- BMI: {user.bmi or "Not calculated"}
- Daily calorie goal: {user.calorie_goal or "Not set"} kcal
- Estimated TDEE: {user.tdee or "Not calculated"} kcal
- Protein goal: {user.protein_goal or "Not set"} g
- Carbohydrate goal: {user.carb_goal or "Not set"} g
- Fat goal: {user.fat_goal or "Not set"} g

Guidelines:
- Be specific and actionable in your recommendations
- Reference the user's actual food log data when giving advice
- Keep responses concise but informative
- Always encourage healthy, sustainable habits
- If the user has not logged enough data, ask them to log more meals
- Respond in the same language the user writes in
    """
    return profile_info.strip()


def build_user_prompt(
    message: str,
    contexts: list[NutritionContext],
    user: User,
) -> str:
    nutrition_summary = "\n".join([
        f"- {ctx.date}: {ctx.total_calories} kcal | "
        f"Protein: {ctx.total_protein}g | "
        f"Carbs: {ctx.total_carbohydrates}g | "
        f"Fat: {ctx.total_fat}g | "
        f"Meals: {len(ctx.meals)}"
        for ctx in contexts
    ])

    meal_details = []
    for ctx in contexts[-3:]:
        if ctx.meals:
            meal_details.append(f"\n{ctx.date}:")
            for meal in ctx.meals:
                meal_details.append(
                    f"  [{meal['meal_type']}] {meal['food_name']} "
                    f"({meal['calories']} kcal, {meal['serving_size']}g)"
                )

    prompt = f"""
Nutrition history for the past {len(contexts)} days:

Daily Summary:
{nutrition_summary}

Recent meal details:
{''.join(meal_details) if meal_details else 'No meals logged recently'}

Daily calorie goal: {user.calorie_goal or 'Not set'} kcal

User question: {message}
    """
    return prompt.strip()


async def stream_claude_response(
    system_prompt: str,
    user_prompt: str,
) -> AsyncGenerator[str, None]:
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"
    yield "data: [DONE]\n\n"


# ==========================================
# Endpoints
# ==========================================

@router.post("/", response_model=AdviceResponse)
async def get_advice(
    payload: AdviceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    days = min(payload.date_range or 7, 30)

    contexts = await get_nutrition_context(current_user.id, days, db)

    if not any(ctx.meals for ctx in contexts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No food logs found. Please log some meals first.",
        )

    system_prompt = build_system_prompt(current_user)
    user_prompt = build_user_prompt(payload.message, contexts, current_user)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return AdviceResponse(
        advice=message.content[0].text,
        based_on_days=days,
        generated_at=datetime.now(),
    )


@router.post("/stream")
async def get_advice_stream(
    payload: AdviceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    days = min(payload.date_range or 7, 30)

    contexts = await get_nutrition_context(current_user.id, days, db)

    if not any(ctx.meals for ctx in contexts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No food logs found. Please log some meals first.",
        )

    system_prompt = build_system_prompt(current_user)
    user_prompt = build_user_prompt(payload.message, contexts, current_user)

    return StreamingResponse(
        stream_claude_response(system_prompt, user_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/daily-tip")
async def get_daily_tip(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contexts = await get_nutrition_context(current_user.id, 1, db)
    today_context = contexts[0] if contexts else None

    if not today_context or not today_context.meals:
        return {"tip": "Start logging your meals today to get personalized nutrition tips!"}

    system_prompt = build_system_prompt(current_user)
    user_prompt = f"""
Based on today's meals:
{json.dumps([m for m in today_context.meals], indent=2)}

Total calories today: {today_context.total_calories} kcal
Calorie goal: {current_user.calorie_goal or 'Not set'} kcal

Give a short, encouraging daily tip (max 3 sentences) based on what the user ate today.
    """.strip()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return {
        "tip": message.content[0].text,
        "date": date.today(),
        "based_on_meals": len(today_context.meals),
    }


@router.get("/weekly-report")
async def get_weekly_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contexts = await get_nutrition_context(current_user.id, 7, db)

    days_with_data = [ctx for ctx in contexts if ctx.meals]
    if len(days_with_data) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 3 days of food logs to generate a weekly report.",
        )

    system_prompt = build_system_prompt(current_user)
    user_prompt = f"""
Generate a weekly nutrition report based on the past 7 days of data.

Weekly data:
{json.dumps([{
    'date': str(ctx.date),
    'calories': ctx.total_calories,
    'protein': ctx.total_protein,
    'carbohydrates': ctx.total_carbohydrates,
    'fat': ctx.total_fat,
    'meals_logged': len(ctx.meals),
} for ctx in contexts], indent=2)}

Calorie goal: {current_user.calorie_goal or 'Not set'} kcal/day

Please provide:
1. Overall assessment of the week
2. Top 2 strengths in their diet
3. Top 2 areas for improvement
4. Specific recommendations for next week
    """.strip()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return {
        "report": message.content[0].text,
        "week_start": str(contexts[0].date),
        "week_end": str(contexts[-1].date),
        "days_logged": len(days_with_data),
        "generated_at": datetime.now(),
    }