from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
import uuid

from database.connection import get_db
from models.food_log import FoodLog
from models.user import User
from routers.auth import get_current_user

router = APIRouter()


# ==========================================
# Pydantic Schemas
# ==========================================

class FoodLogCreate(BaseModel):
    food_name: str
    food_name_en: Optional[str] = None
    image_url: Optional[str] = None
    confidence: Optional[float] = None
    calories: float
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    serving_size: float = 100.0
    serving_unit: str = "g"
    meal_type: str                          # breakfast / lunch / dinner / snack
    eaten_at: datetime
    note: Optional[str] = None
    ml_raw: Optional[dict] = None
    usda_raw: Optional[dict] = None


class FoodLogUpdate(BaseModel):
    serving_size: Optional[float] = None
    meal_type: Optional[str] = None
    eaten_at: Optional[datetime] = None
    note: Optional[str] = None


class FoodLogResponse(BaseModel):
    id: str
    food_name: str
    food_name_en: Optional[str]
    image_url: Optional[str]
    confidence: Optional[float]
    calories: float
    protein: Optional[float]
    carbohydrates: Optional[float]
    fat: Optional[float]
    fiber: Optional[float]
    serving_size: float
    serving_unit: str
    meal_type: str
    eaten_at: datetime
    note: Optional[str]
    total_calories: float
    total_protein: Optional[float]
    total_carbohydrates: Optional[float]
    total_fat: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class DailySummary(BaseModel):
    date: date
    total_calories: float
    total_protein: float
    total_carbohydrates: float
    total_fat: float
    calorie_goal: Optional[float]
    goal_percentage: Optional[float]        # % achieved compared to the target
    meals: dict                             # Breakdown by meal


class WeeklySummary(BaseModel):
    week_start: date
    week_end: date
    daily_summaries: list[DailySummary]
    avg_calories: float
    avg_protein: float
    avg_carbohydrates: float
    avg_fat: float
    calorie_goal: Optional[float]


# ==========================================
# Helper functions
# ==========================================

def validate_meal_type(meal_type: str):
    valid = ["breakfast", "lunch", "dinner", "snack"]
    if meal_type not in valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"meal_type must be one of: {', '.join(valid)}",
        )


async def get_log_or_404(log_id: str, user_id: str, db: AsyncSession) -> FoodLog:
    result = await db.execute(
        select(FoodLog).where(
            and_(FoodLog.id == log_id, FoodLog.user_id == user_id)
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food log not found",
        )
    return log


# ==========================================
# Endpoints
# ==========================================

@router.post("/", response_model=FoodLogResponse, status_code=status.HTTP_201_CREATED)
async def create_log(
    payload: FoodLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    validate_meal_type(payload.meal_type)

    log = FoodLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(log)
    await db.flush()
    return log


@router.get("/", response_model=list[FoodLogResponse])
async def get_logs(
    date: Optional[date] = Query(None, description="Filter by date, e.g., 2024-01-15"),
    meal_type: Optional[str] = Query(None, description="breakfast/lunch/dinner/snack"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(FoodLog).where(FoodLog.user_id == current_user.id)

    if date:
        query = query.where(
            and_(
                extract("year", FoodLog.eaten_at) == date.year,
                extract("month", FoodLog.eaten_at) == date.month,
                extract("day", FoodLog.eaten_at) == date.day,
            )
        )

    if meal_type:
        validate_meal_type(meal_type)
        query = query.where(FoodLog.meal_type == meal_type)

    query = query.order_by(FoodLog.eaten_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/daily-summary", response_model=DailySummary)
async def get_daily_summary(
    date: date = Query(..., description="Target date, e.g., 2024-01-15"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FoodLog).where(
            and_(
                FoodLog.user_id == current_user.id,
                extract("year", FoodLog.eaten_at) == date.year,
                extract("month", FoodLog.eaten_at) == date.month,
                extract("day", FoodLog.eaten_at) == date.day,
            )
        )
    )
    logs = result.scalars().all()

    # Calculate total nutrients
    total_calories = sum(log.total_calories or 0 for log in logs)
    total_protein = sum(log.total_protein or 0 for log in logs)
    total_carbs = sum(log.total_carbohydrates or 0 for log in logs)
    total_fat = sum(log.total_fat or 0 for log in logs)

    # Meal breakdown
    meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
    for log in logs:
        meals[log.meal_type].append({
            "food_name": log.food_name,
            "calories": log.total_calories,
            "serving_size": log.serving_size,
        })

    # Calculate goal percentage
    goal_percentage = None
    if current_user.calorie_goal and current_user.calorie_goal > 0:
        goal_percentage = round(total_calories / current_user.calorie_goal * 100, 1)

    return DailySummary(
        date=date,
        total_calories=round(total_calories, 1),
        total_protein=round(total_protein, 1),
        total_carbohydrates=round(total_carbs, 1),
        total_fat=round(total_fat, 1),
        calorie_goal=current_user.calorie_goal,
        goal_percentage=goal_percentage,
        meals=meals,
    )


@router.get("/weekly-summary", response_model=WeeklySummary)
async def get_weekly_summary(
    week_start: date = Query(..., description="Start date of the week, e.g., 2024-01-15"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta

    week_end = week_start + timedelta(days=6)

    result = await db.execute(
        select(FoodLog).where(
            and_(
                FoodLog.user_id == current_user.id,
                FoodLog.eaten_at >= datetime.combine(week_start, datetime.min.time()),
                FoodLog.eaten_at <= datetime.combine(week_end, datetime.max.time()),
            )
        ).order_by(FoodLog.eaten_at)
    )
    logs = result.scalars().all()

    # Group by day
    from collections import defaultdict
    logs_by_date = defaultdict(list)
    for log in logs:
        logs_by_date[log.eaten_at.date()].append(log)

    # Create daily summaries
    daily_summaries = []
    for i in range(7):
        from datetime import timedelta as td
        current_date = week_start + td(days=i)
        day_logs = logs_by_date.get(current_date, [])

        total_cal = sum(log.total_calories or 0 for log in day_logs)
        total_pro = sum(log.total_protein or 0 for log in day_logs)
        total_carb = sum(log.total_carbohydrates or 0 for log in day_logs)
        total_fat = sum(log.total_fat or 0 for log in day_logs)

        goal_pct = None
        if current_user.calorie_goal and current_user.calorie_goal > 0:
            goal_pct = round(total_cal / current_user.calorie_goal * 100, 1)

        daily_summaries.append(DailySummary(
            date=current_date,
            total_calories=round(total_cal, 1),
            total_protein=round(total_pro, 1),
            total_carbohydrates=round(total_carb, 1),
            total_fat=round(total_fat, 1),
            calorie_goal=current_user.calorie_goal,
            goal_percentage=goal_pct,
            meals={},
        ))

    # Weekly averages
    avg_calories = round(sum(d.total_calories for d in daily_summaries) / 7, 1)
    avg_protein = round(sum(d.total_protein for d in daily_summaries) / 7, 1)
    avg_carbs = round(sum(d.total_carbohydrates for d in daily_summaries) / 7, 1)
    avg_fat = round(sum(d.total_fat for d in daily_summaries) / 7, 1)

    return WeeklySummary(
        week_start=week_start,
        week_end=week_end,
        daily_summaries=daily_summaries,
        avg_calories=avg_calories,
        avg_protein=avg_protein,
        avg_carbohydrates=avg_carbs,
        avg_fat=avg_fat,
        calorie_goal=current_user.calorie_goal,
    )


@router.get("/{log_id}", response_model=FoodLogResponse)
async def get_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_log_or_404(log_id, current_user.id, db)


@router.put("/{log_id}", response_model=FoodLogResponse)
async def update_log(
    log_id: str,
    payload: FoodLogUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    log = await get_log_or_404(log_id, current_user.id, db)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(log, field, value)

    db.add(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    log = await get_log_or_404(log_id, current_user.id, db)
    await db.delete(log)