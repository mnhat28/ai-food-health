from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database.connection import Base


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Thông tin món ăn
    food_name = Column(String, nullable=False)           # tên món ăn (từ ML model)
    food_name_en = Column(String, nullable=True)         # tên tiếng Anh
    image_url = Column(String, nullable=True)            # URL ảnh trên Cloudinary
    confidence = Column(Float, nullable=True)            # độ tin cậy của ML model (0-1)

    # Dinh dưỡng (trên 100g)
    calories = Column(Float, nullable=False)             # kcal
    protein = Column(Float, nullable=True)               # gram
    carbohydrates = Column(Float, nullable=True)         # gram
    fat = Column(Float, nullable=True)                   # gram
    fiber = Column(Float, nullable=True)                 # gram
    sugar = Column(Float, nullable=True)                 # gram
    sodium = Column(Float, nullable=True)                # mg

    # Khẩu phần
    serving_size = Column(Float, default=100.0)          # gram
    serving_unit = Column(String, default="g")           # g / ml / phần

    # Bữa ăn
    meal_type = Column(String, nullable=False)           # breakfast/lunch/dinner/snack
    eaten_at = Column(DateTime(timezone=True), nullable=False)

    # Dữ liệu thô từ ML và USDA (lưu để debug)
    ml_raw = Column(JSON, nullable=True)                 # top 5 predictions từ model
    usda_raw = Column(JSON, nullable=True)               # response từ USDA API

    # Ghi chú của user
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
        """Tính calo thực tế theo khẩu phần ăn"""
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
        """Tóm tắt dinh dưỡng theo khẩu phần thực tế"""
        return {
            "food_name": self.food_name,
            "serving_size": self.serving_size,
            "calories": self.total_calories,
            "protein": self.total_protein,
            "carbohydrates": self.total_carbohydrates,
            "fat": self.total_fat,
        }