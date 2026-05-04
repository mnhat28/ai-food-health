from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
import uuid

from database.connection import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identification
    usda_fdc_id = Column(String, nullable=True, unique=True, index=True)  # ID from USDA
    food_code = Column(String, nullable=True, index=True)                  # internal code

    # Food name
    name_vi = Column(String, nullable=False, index=True)   # Vietnamese name
    name_en = Column(String, nullable=True, index=True)    # English name
    aliases = Column(JSON, nullable=True)                  # alternative names: ["bun thit nuong", "bun BBQ"]

    # Classification
    category = Column(String, nullable=True)               # Main dish / Dessert / Beverage...
    cuisine = Column(String, default="vietnamese")         # vietnamese / asian / western...
    meal_type = Column(JSON, nullable=True)                # ["breakfast", "lunch", "dinner"]

    # Nutrition per 100g
    calories = Column(Float, nullable=False)               # kcal
    protein = Column(Float, nullable=True)                 # grams
    carbohydrates = Column(Float, nullable=True)           # grams
    fat = Column(Float, nullable=True)                     # grams
    fiber = Column(Float, nullable=True)                   # grams
    sugar = Column(Float, nullable=True)                   # grams
    sodium = Column(Float, nullable=True)                  # mg
    cholesterol = Column(Float, nullable=True)             # mg
    saturated_fat = Column(Float, nullable=True)           # grams

    # Default serving
    default_serving_size = Column(Float, default=100.0)    # grams
    default_serving_unit = Column(String, default="g")     # g / ml / portion / bowl

    # ML
    ml_label = Column(String, nullable=True, index=True)   # label returned by model, e.g.: "pho_bo"
    ml_label_aliases = Column(JSON, nullable=True)         # other labels for the same food

    # Additional information
    description = Column(String, nullable=True)            # short description
    ingredients = Column(JSON, nullable=True)              # main ingredients
    allergens = Column(JSON, nullable=True)                # ["gluten", "lactose", "nuts"]
    tags = Column(JSON, nullable=True)                     # ["low-carb", "high-protein"]

    # Status
    is_verified = Column(Boolean, default=False)           # whether it has been verified
    is_active = Column(Boolean, default=True)
    source = Column(String, default="usda")                # usda / manual / community

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<FoodItem {self.name_vi}>"

    @property
    def nutrition_per_100g(self):
        """Return nutrition per 100g as a dict"""
        return {
            "calories": self.calories,
            "protein": self.protein,
            "carbohydrates": self.carbohydrates,
            "fat": self.fat,
            "fiber": self.fiber,
            "sugar": self.sugar,
            "sodium": self.sodium,
        }

    def nutrition_for_serving(self, serving_size: float):
        """Calculate nutrition for any serving size"""
        ratio = serving_size / 100

        def scale(val):
            return round(val * ratio, 1) if val else None

        return {
            "serving_size": serving_size,
            "serving_unit": self.default_serving_unit,
            "calories": scale(self.calories),
            "protein": scale(self.protein),
            "carbohydrates": scale(self.carbohydrates),
            "fat": scale(self.fat),
            "fiber": scale(self.fiber),
            "sugar": scale(self.sugar),
            "sodium": scale(self.sodium),
        }

    @property
    def glycemic_estimate(self):
        """Estimate glycemic index based on carbs and fiber"""
        if not self.carbohydrates:
            return None
        net_carb = self.carbohydrates - (self.fiber or 0)
        if net_carb < 10:
            return "low"
        elif net_carb < 25:
            return "medium"
        return "high"