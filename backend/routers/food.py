from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import httpx
import cloudinary
import cloudinary.uploader
import os

from database.connection import get_db
from models.food_log import FoodLog
from models.food_item import FoodItem
from models.user import User
from routers.auth import get_current_user

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml:8001")

router = APIRouter()


# ==========================================
# Pydantic Schemas
# ==========================================

class PredictionResult(BaseModel):
    food_name: str
    food_name_en: str
    confidence: float
    calories: float
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sodium: Optional[float] = None
    serving_size: float = 100.0
    top_predictions: list[dict]
    usda_data: Optional[dict] = None


class FoodSearchResult(BaseModel):
    id: str
    name_vi: str
    name_en: Optional[str]
    calories: float
    protein: Optional[float]
    carbohydrates: Optional[float]
    fat: Optional[float]
    default_serving_size: float
    default_serving_unit: str
    category: Optional[str]

    class Config:
        from_attributes = True


class ManualFoodEntry(BaseModel):
    food_name: str
    calories: float
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    serving_size: float = 100.0
    serving_unit: str = "g"
    meal_type: str
    note: Optional[str] = None


# ==========================================
# Helper functions
# ==========================================

async def upload_image_to_cloudinary(file: UploadFile) -> str:
    contents = await file.read()
    result = cloudinary.uploader.upload(
        contents,
        folder="ai-food-health/food-images",
        resource_type="image",
        transformation=[
            {"width": 800, "height": 800, "crop": "limit"},
            {"quality": "auto"},
        ],
    )
    return result["secure_url"]


async def call_ml_service(image_url: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{ML_SERVICE_URL}/predict",
            json={"image_url": image_url},
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ML service is unavailable",
            )
        return response.json()


async def get_usda_nutrition(food_name_en: str) -> Optional[dict]:
    usda_api_key = os.getenv("USDA_API_KEY")
    if not usda_api_key:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://api.nal.usda.gov/fdc/v1/foods/search",
            params={
                "query": food_name_en,
                "api_key": usda_api_key,
                "pageSize": 1,
                "dataType": "Survey (FNDDS)",
            },
        )
        if response.status_code != 200:
            return None

        data = response.json()
        foods = data.get("foods", [])
        if not foods:
            return None

        food = foods[0]
        nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}

        return {
            "fdc_id": food.get("fdcId"),
            "description": food.get("description"),
            "calories": nutrients.get("Energy", 0),
            "protein": nutrients.get("Protein", 0),
            "carbohydrates": nutrients.get("Carbohydrate, by difference", 0),
            "fat": nutrients.get("Total lipid (fat)", 0),
            "fiber": nutrients.get("Fiber, total dietary", 0),
            "sugar": nutrients.get("Sugars, total including NLEA", 0),
            "sodium": nutrients.get("Sodium, Na", 0),
        }


async def get_food_item_from_db(
    ml_label: str,
    db: AsyncSession,
) -> Optional[FoodItem]:
    result = await db.execute(
        select(FoodItem).where(FoodItem.ml_label == ml_label)
    )
    return result.scalar_one_or_none()


# ==========================================
# Endpoints
# ==========================================

@router.post("/analyze", response_model=PredictionResult)
async def analyze_food_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are supported",
        )

    # Validate file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size must be less than 10MB",
        )
    await file.seek(0)

    # Upload image to Cloudinary
    image_url = await upload_image_to_cloudinary(file)

    # Call ML service
    ml_result = await call_ml_service(image_url)

    top_prediction = ml_result["predictions"][0]
    food_name_en = top_prediction["label"]
    confidence = top_prediction["confidence"]

    # Look up food item in local database first
    food_item = await get_food_item_from_db(food_name_en, db)

    if food_item:
        return PredictionResult(
            food_name=food_item.name_vi,
            food_name_en=food_item.name_en or food_name_en,
            confidence=confidence,
            calories=food_item.calories,
            protein=food_item.protein,
            carbohydrates=food_item.carbohydrates,
            fat=food_item.fat,
            fiber=food_item.fiber,
            sodium=food_item.sodium,
            serving_size=food_item.default_serving_size,
            top_predictions=ml_result["predictions"],
        )

    # Fallback to USDA API if not in local database
    usda_data = await get_usda_nutrition(food_name_en)

    if not usda_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nutrition data not found for: {food_name_en}",
        )

    return PredictionResult(
        food_name=food_name_en,
        food_name_en=food_name_en,
        confidence=confidence,
        calories=usda_data.get("calories", 0),
        protein=usda_data.get("protein"),
        carbohydrates=usda_data.get("carbohydrates"),
        fat=usda_data.get("fat"),
        fiber=usda_data.get("fiber"),
        sodium=usda_data.get("sodium"),
        serving_size=100.0,
        top_predictions=ml_result["predictions"],
        usda_data=usda_data,
    )


@router.get("/search", response_model=list[FoodSearchResult])
async def search_food(
    query: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FoodItem).where(
            FoodItem.name_vi.ilike(f"%{query}%") |
            FoodItem.name_en.ilike(f"%{query}%")
        ).limit(limit)
    )
    return result.scalars().all()


@router.get("/search/usda", response_model=list[dict])
async def search_usda(
    query: str,
    current_user: User = Depends(get_current_user),
):
    usda_data = await get_usda_nutrition(query)
    if not usda_data:
        return []
    return [usda_data]


@router.get("/items/{food_id}", response_model=FoodSearchResult)
async def get_food_item(
    food_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FoodItem).where(FoodItem.id == food_id)
    )
    food = result.scalar_one_or_none()
    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food item not found",
        )
    return food