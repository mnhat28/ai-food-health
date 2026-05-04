from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Personal information
    full_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)        # male / female / other
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)

    # Nutrition goals
    calorie_goal = Column(Float, nullable=True)   # target calories per day
    protein_goal = Column(Float, nullable=True)   # grams
    carb_goal = Column(Float, nullable=True)      # grams
    fat_goal = Column(Float, nullable=True)       # grams

    # Settings
    email_reminder = Column(Boolean, default=True)   # enable/disable email reminders
    reminder_time = Column(String, default="20:00")  # email sending time

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    food_logs = relationship("FoodLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @property
    def tdee(self):
        """Calculate total daily energy expenditure (Harris-Benedict)"""
        if not all([self.age, self.gender, self.height_cm, self.weight_kg]):
            return None
        if self.gender == "male":
            bmr = 88.36 + (13.4 * self.weight_kg) + (4.8 * self.height_cm) - (5.7 * self.age)
        else:
            bmr = 447.6 + (9.2 * self.weight_kg) + (3.1 * self.height_cm) - (4.3 * self.age)
        return round(bmr * 1.55, 1)  # moderate activity level