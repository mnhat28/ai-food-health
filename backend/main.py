from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database.connection import init_db
from routers import auth, food, logs, advice


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AI Food Health API",
    description="API nhận diện món ăn, ước lượng calo và đưa lời khuyên dinh dưỡng",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(food.router, prefix="/api/food", tags=["Food"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(advice.router, prefix="/api/advice", tags=["Advice"])


@app.get("/")
async def root():
    return {"message": "AI Food Health API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}