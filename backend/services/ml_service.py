import httpx
import logging
from typing import Optional
from pydantic import BaseModel
import os

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml:8001")
ML_TIMEOUT = float(os.getenv("ML_TIMEOUT", 30.0))

logger = logging.getLogger(__name__)


# ==========================================
# Pydantic Schemas
# ==========================================

class SinglePrediction(BaseModel):
    label: str
    confidence: float
    rank: int


class MLPredictionResponse(BaseModel):
    success: bool
    top_prediction: SinglePrediction
    all_predictions: list[SinglePrediction]
    inference_time_ms: float
    model_version: str


class MLHealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float


# ==========================================
# ML Service Client
# ==========================================

class MLServiceClient:

    def __init__(self):
        self.base_url = ML_SERVICE_URL
        self.timeout = ML_TIMEOUT

    async def health_check(self) -> MLHealthResponse | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return MLHealthResponse(**response.json())
                return None
        except Exception as e:
            logger.error(f"[MLService] Health check failed: {e}")
            return None

    async def predict_from_url(self, image_url: str) -> MLPredictionResponse | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/predict",
                    json={"image_url": image_url},
                )
                if response.status_code == 200:
                    return MLPredictionResponse(**response.json())

                logger.error(
                    f"[MLService] Predict failed — "
                    f"status: {response.status_code}, "
                    f"body: {response.text}"
                )
                return None

        except httpx.TimeoutException:
            logger.error(f"[MLService] Predict timed out after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"[MLService] Predict error: {e}")
            return None

    async def predict_from_bytes(self, image_bytes: bytes, filename: str) -> MLPredictionResponse | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/predict/upload",
                    files={"file": (filename, image_bytes, "image/jpeg")},
                )
                if response.status_code == 200:
                    return MLPredictionResponse(**response.json())

                logger.error(
                    f"[MLService] Predict upload failed — "
                    f"status: {response.status_code}, "
                    f"body: {response.text}"
                )
                return None

        except httpx.TimeoutException:
            logger.error(f"[MLService] Predict upload timed out after {self.timeout}s")
            return None
        except Exception as e:
            logger.error(f"[MLService] Predict upload error: {e}")
            return None

    async def get_model_info(self) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/model/info")
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"[MLService] Get model info failed: {e}")
            return None

    async def is_available(self) -> bool:
        health = await self.health_check()
        return health is not None and health.model_loaded


# ==========================================
# Utility functions
# ==========================================

def filter_low_confidence(
    predictions: list[SinglePrediction],
    threshold: float = 0.3,
) -> list[SinglePrediction]:
    return [p for p in predictions if p.confidence >= threshold]


def is_confident_prediction(
    prediction: SinglePrediction,
    threshold: float = 0.6,
) -> bool:
    return prediction.confidence >= threshold


def format_predictions_for_log(
    predictions: list[SinglePrediction],
) -> list[dict]:
    return [
        {
            "rank": p.rank,
            "label": p.label,
            "confidence": round(p.confidence, 4),
        }
        for p in predictions
    ]


ml_client = MLServiceClient()