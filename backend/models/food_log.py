from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database.connection import Base


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Food information
    food_name = Column(String, nullable=False)           # food name (from ML model)
    food_name_en = Column(String, nullable=True)         # English name
    image_url = Column(String, nullable=True)            # image URL on Cloudinary
    confidence = Column(Float, nullable=True)            # ML model confidence (0-1)

    # Nutrition (per 100g)
    calories = Column(Float, nullable=False)             # kcal
    protein = Column(Float, nullable=True)               # grams
    carbohydrates = Column(Float, nullable=True)         # grams
    fat = Column(Float, nullable=True)                   # grams
    fiber = Column(Float, nullable=True)                 # grams
    sugar = Column(Float, nullable=True)                 # grams
    sodium = Column(Float, nullable=True)                # mg

    # Serving size
    serving_size = Column(Float, default=100.0)          # grams
    serving_unit = Column(String, default="g")           # g / ml / portion

    # Meal
    meal_type = Column(String, nullable=False)           # breakfast/lunch/dinner/snack
    eaten_at = Column(DateTime(timezone=True), nullable=False)

    # Raw data from ML and USDA (stored for debugging)
    ml_raw = Column(JSON, nullable=True)                 # top 5 predictions from model
    usda_raw = Column(JSON, nullable=True)               # response from USDA API

    # User note
    note = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="food_logs")

    def __repr__(self):
        return f"<FoodLog {self.food_name} - {self.eaten_at}>"

    @property
    def total_calories(self):
        """Calculate actual calories based on serving size"""
        if self.calories and self.serving_size:
            return round(self.calories * self.serving_size / 100, 1)
        return self.calories

    @property
    def total_protein(self):
        if self.protein and self.serving_size:
            return round(self.protein * self.serving_size / 100, 1)
        return self.protein

    @property
    def total_carbohydrates(self):
        if self.carbohydrates and self.serving_size:
            return round(self.carbohydrates * self.serving_size / 100, 1)
        return self.carbohydrates

    @property
    def total_fat(self):
        if self.fat and self.serving_size:
            return round(self.fat * self.serving_size / 100, 1)
        return self.fat

    @property
    def nutrition_summary(self):
        """Nutrition summary based on actual serving size"""
        return {
            "food_name": self.food_name,
            "serving_size": self.serving_size,
            "calories": self.total_calories,
            "protein": self.total_protein,
            "carbohydrates": self.total_carbohydrates,
            "fat": self.total_fat,
        }