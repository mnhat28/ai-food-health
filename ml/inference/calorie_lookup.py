import httpx
import logging
import json
import os
import time
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
CACHE_PATH = os.getenv("CALORIE_CACHE_PATH", "./data/calorie_cache.json")


# ==========================================
# Pydantic Schemas
# ==========================================

class NutritionInfo(BaseModel):
    fdc_id: Optional[str] = None
    food_name: str
    calories: float
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    cholesterol: Optional[float] = None
    serving_size: float = 100.0
    serving_unit: str = "g"
    source: str = "usda"


# ==========================================
# Local cache
# ==========================================

class NutritionCache:

    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"[Cache] Loaded {len(self._cache)} cached entries")
            except Exception as e:
                logger.error(f"[Cache] Failed to load cache: {e}")
                self._cache = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[Cache] Failed to save cache: {e}")

    def get(self, key: str) -> Optional[dict]:
        entry = self._cache.get(key.lower().strip())
        if entry:
            logger.info(f"[Cache] Hit for: {key}")
        return entry

    def set(self, key: str, value: dict):
        self._cache[key.lower().strip()] = value
        self._save()
        logger.info(f"[Cache] Saved entry for: {key}")

    def has(self, key: str) -> bool:
        return key.lower().strip() in self._cache

    def size(self) -> int:
        return len(self._cache)


# ==========================================
# USDA API client
# ==========================================

class USDAClient:

    def __init__(self):
        self.api_key = USDA_API_KEY
        self.base_url = USDA_BASE_URL

    async def search(self, query: str, page_size: int = 5) -> list[dict]:
        if not self.api_key:
            logger.warning("[USDA] API key not set")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/foods/search",
                    params={
                        "query": query,
                        "api_key": self.api_key,
                        "pageSize": page_size,
                        "dataType": "Survey (FNDDS),SR Legacy",
                    },
                )
                if response.status_code != 200:
                    logger.error(f"[USDA] Search failed: {response.status_code}")
                    return []

                data = response.json()
                return data.get("foods", [])

        except Exception as e:
            logger.error(f"[USDA] Search error for '{query}': {e}")
            return []

    async def get_food_detail(self, fdc_id: str) -> Optional[dict]:
        if not self.api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/food/{fdc_id}",
                    params={"api_key": self.api_key},
                )
                if response.status_code != 200:
                    return None
                return response.json()

        except Exception as e:
            logger.error(f"[USDA] Get detail error for fdc_id {fdc_id}: {e}")
            return None

    def parse_nutrients(self, food: dict) -> dict:
        nutrient_map = {
            "Energy": "calories",
            "Protein": "protein",
            "Carbohydrate, by difference": "carbohydrates",
            "Total lipid (fat)": "fat",
            "Fiber, total dietary": "fiber",
            "Sugars, total including NLEA": "sugar",
            "Sodium, Na": "sodium",
            "Cholesterol": "cholesterol",
        }

        nutrients = {}
        for nutrient in food.get("foodNutrients", []):
            name = nutrient.get("nutrientName") or nutrient.get("name", "")
            value = nutrient.get("value") or nutrient.get("amount", 0)
            if name in nutrient_map:
                nutrients[nutrient_map[name]] = round(float(value or 0), 2)

        return nutrients


# ==========================================
# Vietnamese food fallback database
# ==========================================

VIETNAMESE_FOOD_DB: dict[str, NutritionInfo] = {
    "pho_bo": NutritionInfo(
        food_name="Pho Bo",
        calories=86, protein=6.0, carbohydrates=12.0,
        fat=1.5, fiber=0.5, sodium=620.0,
        serving_size=500, serving_unit="ml", source="manual",
    ),
    "banh_mi": NutritionInfo(
        food_name="Banh Mi",
        calories=270, protein=11.0, carbohydrates=35.0,
        fat=9.0, fiber=1.5, sodium=580.0,
        serving_size=180, serving_unit="g", source="manual",
    ),
    "com_tam": NutritionInfo(
        food_name="Com Tam",
        calories=480, protein=28.0, carbohydrates=58.0,
        fat=14.0, fiber=2.0, sodium=820.0,
        serving_size=400, serving_unit="g", source="manual",
    ),
    "bun_bo_hue": NutritionInfo(
        food_name="Bun Bo Hue",
        calories=92, protein=7.0, carbohydrates=13.0,
        fat=2.0, fiber=0.8, sodium=750.0,
        serving_size=500, serving_unit="ml", source="manual",
    ),
    "goi_cuon": NutritionInfo(
        food_name="Goi Cuon",
        calories=90, protein=5.5, carbohydrates=13.0,
        fat=1.5, fiber=1.2, sodium=320.0,
        serving_size=100, serving_unit="g", source="manual",
    ),
    "banh_xeo": NutritionInfo(
        food_name="Banh Xeo",
        calories=230, protein=10.0, carbohydrates=28.0,
        fat=9.0, fiber=2.0, sodium=510.0,
        serving_size=200, serving_unit="g", source="manual",
    ),
    "hu_tieu": NutritionInfo(
        food_name="Hu Tieu",
        calories=78, protein=5.5, carbohydrates=11.0,
        fat=1.5, fiber=0.5, sodium=580.0,
        serving_size=500, serving_unit="ml", source="manual",
    ),
    "com_chien": NutritionInfo(
        food_name="Com Chien",
        calories=185, protein=6.0, carbohydrates=28.0,
        fat=5.5, fiber=1.0, sodium=420.0,
        serving_size=250, serving_unit="g", source="manual",
    ),
    "bun_thit_nuong": NutritionInfo(
        food_name="Bun Thit Nuong",
        calories=380, protein=22.0, carbohydrates=48.0,
        fat=10.0, fiber=2.5, sodium=690.0,
        serving_size=350, serving_unit="g", source="manual",
    ),
    "canh_chua": NutritionInfo(
        food_name="Canh Chua",
        calories=65, protein=8.0, carbohydrates=6.0,
        fat=1.5, fiber=1.5, sodium=480.0,
        serving_size=300, serving_unit="ml", source="manual",
    ),
}


# ==========================================
# Calorie lookup service
# ==========================================

class CalorieLookupService:

    def __init__(self):
        self.cache = NutritionCache(CACHE_PATH)
        self.usda = USDAClient()

    async def lookup(self, ml_label: str, food_name_en: str) -> Optional[NutritionInfo]:
        # Step 1 — Check Vietnamese food database first
        if ml_label in VIETNAMESE_FOOD_DB:
            logger.info(f"[Lookup] Found in Vietnamese DB: {ml_label}")
            return VIETNAMESE_FOOD_DB[ml_label]

        # Step 2 — Check local cache
        if self.cache.has(ml_label):
            cached = self.cache.get(ml_label)
            return NutritionInfo(**cached)

        if self.cache.has(food_name_en):
            cached = self.cache.get(food_name_en)
            return NutritionInfo(**cached)

        # Step 3 — Query USDA API
        logger.info(f"[Lookup] Querying USDA for: {food_name_en}")
        foods = await self.usda.search(food_name_en)

        if not foods:
            logger.warning(f"[Lookup] No USDA results for: {food_name_en}")
            return None

        food = foods[0]
        nutrients = self.usda.parse_nutrients(food)

        if not nutrients.get("calories"):
            logger.warning(f"[Lookup] No calorie data for: {food_name_en}")
            return None

        nutrition = NutritionInfo(
            fdc_id=str(food.get("fdcId", "")),
            food_name=food.get("description", food_name_en),
            calories=nutrients.get("calories", 0),
            protein=nutrients.get("protein"),
            carbohydrates=nutrients.get("carbohydrates"),
            fat=nutrients.get("fat"),
            fiber=nutrients.get("fiber"),
            sugar=nutrients.get("sugar"),
            sodium=nutrients.get("sodium"),
            cholesterol=nutrients.get("cholesterol"),
            source="usda",
        )

        # Save to cache for future lookups
        self.cache.set(ml_label, nutrition.model_dump())

        return nutrition

    async def lookup_batch(
        self,
        labels: list[str],
    ) -> dict[str, Optional[NutritionInfo]]:
        results = {}
        for label in labels:
            results[label] = await self.lookup(label, label.replace("_", " "))
        return results

    def get_cache_stats(self) -> dict:
        return {
            "cached_entries": self.cache.size(),
            "vietnamese_entries": len(VIETNAMESE_FOOD_DB),
            "cache_path": CACHE_PATH,
        }


calorie_lookup = CalorieLookupService()