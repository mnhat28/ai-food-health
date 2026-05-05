import onnxruntime as ort
import numpy as np
from PIL import Image
import httpx
import io
import time
import logging
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("ML_MODEL_PATH", "./models/food_classifier.onnx")
FOOD_CLASSES_PATH = os.getenv("FOOD_CLASSES_PATH", "./data/food_classes.json")
TOP_K = int(os.getenv("TOP_K", 5))
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")

# Global model state
ort_session: Optional[ort.InferenceSession] = None
food_classes: Optional[list[str]] = None
model_load_time: Optional[float] = None


# ==========================================
# Pydantic Schemas
# ==========================================

class PredictFromURLRequest(BaseModel):
    image_url: str


class SinglePrediction(BaseModel):
    rank: int
    label: str
    confidence: float


class PredictResponse(BaseModel):
    success: bool
    top_prediction: SinglePrediction
    all_predictions: list[SinglePrediction]
    inference_time_ms: float
    model_version: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float


class ModelInfoResponse(BaseModel):
    model_version: str
    num_classes: int
    input_shape: list[int]
    classes_sample: list[str]


# ==========================================
# Model loading
# ==========================================

def load_model():
    global ort_session, food_classes, model_load_time

    if not os.path.exists(MODEL_PATH):
        logger.warning(f"[Predictor] Model not found at {MODEL_PATH}")
        logger.warning("[Predictor] Running in mock mode for development")
        return

    logger.info(f"[Predictor] Loading ONNX model from {MODEL_PATH}")
    start = time.time()

    ort_session = ort.InferenceSession(
        MODEL_PATH,
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    import json
    with open(FOOD_CLASSES_PATH, "r", encoding="utf-8") as f:
        food_classes = json.load(f)

    model_load_time = time.time()
    elapsed = round((model_load_time - start) * 1000, 2)
    logger.info(f"[Predictor] Model loaded in {elapsed}ms — {len(food_classes)} classes")


# ==========================================
# Image preprocessing
# ==========================================

def preprocess_image(image: Image.Image) -> np.ndarray:
    # Resize to 224x224 (EfficientNet input size)
    image = image.convert("RGB")
    image = image.resize((224, 224), Image.LANCZOS)

    # Convert to numpy array
    img_array = np.array(image, dtype=np.float32)

    # Normalize with ImageNet mean and std
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_array = (img_array / 255.0 - mean) / std

    # Convert HWC to CHW then add batch dimension
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)

    return img_array


def softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()


# ==========================================
# Inference
# ==========================================

def run_inference(image: Image.Image) -> list[SinglePrediction]:
    # Mock mode for development when model is not loaded
    if ort_session is None or food_classes is None:
        logger.warning("[Predictor] Running mock inference")
        mock_classes = [
            "pho_bo", "banh_mi", "com_tam",
            "bun_bo_hue", "goi_cuon"
        ]
        return [
            SinglePrediction(
                rank=i + 1,
                label=cls,
                confidence=round(0.9 - i * 0.15, 4),
            )
            for i, cls in enumerate(mock_classes[:TOP_K])
        ]

    start = time.time()

    input_array = preprocess_image(image)

    input_name = ort_session.get_inputs()[0].name
    outputs = ort_session.run(None, {input_name: input_array})

    logits = outputs[0][0]
    probabilities = softmax(logits)

    top_k_indices = np.argsort(probabilities)[::-1][:TOP_K]

    predictions = [
        SinglePrediction(
            rank=i + 1,
            label=food_classes[idx],
            confidence=round(float(probabilities[idx]), 4),
        )
        for i, idx in enumerate(top_k_indices)
    ]

    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(
        f"[Predictor] Inference done in {elapsed}ms — "
        f"top: {predictions[0].label} ({predictions[0].confidence:.2%})"
    )

    return predictions


async def load_image_from_url(image_url: str) -> Image.Image:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(image_url)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch image from URL: {image_url}",
                )
            return Image.open(io.BytesIO(response.content))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image URL: {e}",
        )


async def load_image_from_bytes(file: UploadFile) -> Image.Image:
    try:
        contents = await file.read()
        return Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {e}",
        )


# ==========================================
# FastAPI app
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(
    title="AI Food Health — ML Service",
    description="ONNX model serving for food recognition",
    version=MODEL_VERSION,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    uptime = 0.0
    if model_load_time:
        uptime = round(time.time() - model_load_time, 1)

    return HealthResponse(
        status="healthy",
        model_loaded=ort_session is not None,
        model_version=MODEL_VERSION,
        uptime_seconds=uptime,
    )


@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    if ort_session is None or food_classes is None:
        return ModelInfoResponse(
            model_version=MODEL_VERSION,
            num_classes=0,
            input_shape=[1, 3, 224, 224],
            classes_sample=["mock_mode"],
        )

    input_shape = list(ort_session.get_inputs()[0].shape)

    return ModelInfoResponse(
        model_version=MODEL_VERSION,
        num_classes=len(food_classes),
        input_shape=input_shape,
        classes_sample=food_classes[:10],
    )


@app.post("/predict", response_model=PredictResponse)
async def predict_from_url(payload: PredictFromURLRequest):
    start = time.time()

    image = await load_image_from_url(payload.image_url)
    predictions = run_inference(image)

    inference_time = round((time.time() - start) * 1000, 2)

    return PredictResponse(
        success=True,
        top_prediction=predictions[0],
        all_predictions=predictions,
        inference_time_ms=inference_time,
        model_version=MODEL_VERSION,
    )


@app.post("/predict/upload", response_model=PredictResponse)
async def predict_from_upload(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are supported",
        )

    start = time.time()

    image = await load_image_from_bytes(file)
    predictions = run_inference(image)

    inference_time = round((time.time() - start) * 1000, 2)

    return PredictResponse(
        success=True,
        top_prediction=predictions[0],
        all_predictions=predictions,
        inference_time_ms=inference_time,
        model_version=MODEL_VERSION,
    )