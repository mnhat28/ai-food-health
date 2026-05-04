from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
import uuid

from database.connection import Base


class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Định danh
    usda_fdc_id = Column(String, nullable=True, unique=True, index=True)  # ID từ USDA
    food_code = Column(String, nullable=True, index=True)                  # mã nội bộ

    # Tên món ăn
    name_vi = Column(String, nullable=False, index=True)   # tên tiếng Việt
    name_en = Column(String, nullable=True, index=True)    # tên tiếng Anh
    aliases = Column(JSON, nullable=True)                  # tên gọi khác: ["bún thịt nướng", "bún BBQ"]

    # Phân loại
    category = Column(String, nullable=True)               # Món chính / Tráng miệng / Đồ uống...
    cuisine = Column(String, default="vietnamese")         # vietnamese / asian / western...
    meal_type = Column(JSON, nullable=True)                # ["breakfast", "lunch", "dinner"]

    # Dinh dưỡng trên 100g
    calories = Column(Float, nullable=False)               # kcal
    protein = Column(Float, nullable=True)                 # gram
    carbohydrates = Column(Float, nullable=True)           # gram
    fat = Column(Float, nullable=True)                     # gram
    fiber = Column(Float, nullable=True)                   # gram
    sugar = Column(Float, nullable=True)                   # gram
    sodium = Column(Float, nullable=True)                  # mg
    cholesterol = Column(Float, nullable=True)             # mg
    saturated_fat = Column(Float, nullable=True)           # gram

    # Khẩu phần chuẩn
    default_serving_size = Column(Float, default=100.0)    # gram
    default_serving_unit = Column(String, default="g")     # g / ml / phần / tô / bát

    # ML
    ml_label = Column(String, nullable=True, index=True)   # nhãn model trả về, vd: "pho_bo"
    ml_label_aliases = Column(JSON, nullable=True)         # các nhãn khác cùng món

    # Thông tin thêm
    description = Column(String, nullable=True)            # mô tả ngắn
    ingredients = Column(JSON, nullable=True)              # nguyên liệu chính
    allergens = Column(JSON, nullable=True)                # ["gluten", "lactose", "nuts"]
    tags = Column(JSON, nullable=True)                     # ["low-carb", "high-protein"]

    # Trạng thái
    is_verified = Column(Boolean, default=False)           # đã được kiểm duyệt chưa
    is_active = Column(Boolean, default=True)
    source = Column(String, default="usda")                # usda / manual / community

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<FoodItem {self.name_vi}>"

    @property
    def nutrition_per_100g(self):
        """Trả về dinh dưỡng trên 100g dạng dict"""
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
        """Tính dinh dưỡng theo khẩu phần bất kỳ"""
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
        """Ước tính chỉ số đường huyết đơn giản dựa trên carb và fiber"""
        if not self.carbohydrates:
            return None
        net_carb = self.carbohydrates - (self.fiber or 0)
        if net_carb < 10:
            return "low"
        elif net_carb < 25:
            return "medium"
        return "high"