# 🥗 AI Food Health Assistant

A full-stack web application that uses machine learning to recognize food from photos, estimate calories, track eating history, and provide personalized nutrition advice powered by Google Gemini AI.

---

## ✨ Features

- 📸 **Food Recognition** — Upload a photo and get instant food identification powered by EfficientNet-B4
- 🔥 **Calorie Estimation** — Automatic nutrition data from USDA FoodData Central API
- 📊 **Weekly Dashboard** — Nutrition charts, calorie progress, streak tracking
- 📅 **Food History** — Calendar-based log with meal grouping, search and filter
- 🤖 **AI Nutrition Advice** — Personalized recommendations powered by Google Gemini
- 📧 **Email Reminders** — Daily nutrition summaries and weekly AI reports via SendGrid
- 🔐 **Authentication** — Secure JWT-based login and registration

---

## 🏗️ System Architecture

```
ai-food-health/
├── ml/                          # Machine Learning pipeline
│   ├── data/
│   │   ├── food_classes.json    # 108 food class labels
│   │   ├── raw/                 # Raw dataset (Food-101 + Vietnamese food)
│   │   └── processed/           # Train/val split
│   ├── training/
│   │   ├── train.py             # EfficientNet-B4 training loop
│   │   ├── dataset.py           # DataLoader + augmentation
│   │   ├── evaluate.py          # Metrics + visualizations
│   │   └── export_onnx.py       # PyTorch → ONNX export
│   ├── inference/
│   │   ├── predictor.py         # ONNX model FastAPI server
│   │   └── calorie_lookup.py    # USDA API + Vietnamese food DB
│   └── models/
│       ├── food_classifier.pt   # PyTorch checkpoint
│       ├── food_classifier.onnx # ONNX model for serving
│       └── model_metadata.json  # Model info + benchmark
├── backend/                     # FastAPI REST API
│   ├── main.py
│   ├── routers/
│   │   ├── auth.py              # JWT authentication
│   │   ├── food.py              # Image upload + ML inference
│   │   ├── logs.py              # Food log CRUD + summaries
│   │   └── advice.py            # Gemini AI advice
│   ├── models/
│   │   ├── user.py              # User ORM model
│   │   ├── food_log.py          # FoodLog ORM model
│   │   └── food_item.py         # FoodItem ORM model
│   ├── services/
│   │   ├── email_service.py     # SendGrid HTML emails
│   │   ├── scheduler.py         # Daily/weekly cron jobs
│   │   └── ml_service.py        # ML service HTTP client
│   └── database/
│       └── connection.py        # PostgreSQL async connection
├── frontend/                    # Next.js 14 web app
│   ├── app/
│   │   ├── page.tsx             # Home + food upload
│   │   ├── dashboard/           # Weekly nutrition charts
│   │   ├── history/             # Calendar food history
│   │   ├── advice/              # AI chat interface
│   │   └── auth/                # Login + register
│   ├── components/
│   │   ├── FoodUploader.tsx     # Drag & drop + ML analysis
│   │   ├── CalorieChart.tsx     # Recharts weekly chart
│   │   ├── FoodLogCard.tsx      # Expandable log card
│   │   └── NutritionBadge.tsx   # Multi-variant nutrition display
│   └── lib/
│       ├── api.ts               # Axios API client
│       └── auth.ts              # JWT token management
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## 🧠 ML Model Training

### Dataset

| Source | Classes | Images |
|--------|---------|--------|
| Food-101 | 73 international classes | ~73,000 |
| Vietnamese food (scraped) | 35 Vietnamese classes | ~7,000 |
| **Total** | **108 classes** | **~80,000** |

**Vietnamese food classes include:** Phở bò, Bánh mì, Cơm tấm, Bún bò Huế, Gỏi cuốn, Bánh xèo, Bún thịt nướng, Cá kho tộ, Canh chua, Cao lầu, and 25 more.

### Model Architecture

```
Input (224×224×3)
    ↓
EfficientNet-B4 (pretrained on ImageNet)
    ↓
Global Average Pooling
    ↓
Dropout (p=0.3)
    ↓
Linear (1792 → 108)
    ↓
Output (108 classes)
```

### Training Configuration

```python
model         = EfficientNet-B4 (pretrained)
optimizer     = AdamW(lr=3e-4, weight_decay=1e-4)
scheduler     = LinearWarmup(3 epochs) → CosineAnnealingLR
loss          = CrossEntropyLoss(label_smoothing=0.1)
epochs        = 30 (early stopping patience=7)
batch_size    = 32
image_size    = 224×224
mixed_precision = True (AMP)
grad_clip     = 1.0
```

### Data Augmentation

```python
# Training transforms
RandomResizedCrop(224, scale=(0.7, 1.0))
HorizontalFlip(p=0.5)
RandomBrightnessContrast(p=0.5)
HueSaturationValue(p=0.4)
ShiftScaleRotate(rotate_limit=15, p=0.4)
GaussianBlur / MotionBlur / MedianBlur (p=0.2)
CoarseDropout(max_holes=8, p=0.2)
Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

# Validation transforms
Resize(256) → CenterCrop(224) → Normalize
```

### Training Progress

| Epoch | Train Loss | Train Top-1 | Val Loss | Val Top-1 | Val Top-5 |
|-------|-----------|------------|---------|----------|---------|
| 1 | 2.8412 | 45.23% | 2.1034 | 62.41% | 84.12% |
| 2 | 1.9823 | 68.47% | 1.6821 | 74.85% | 92.34% |
| 3 | 1.6234 | 76.91% | 1.5012 | 79.32% | 94.21% |
| 4 | 1.4156 | 82.34% | 1.3421 | 83.74% | 96.12% |
| 5 | 1.2305 | 87.19% | 1.2705 | 86.84% | 97.39% |
| 6 | 1.1446 | 89.81% | 1.2460 | 87.50% | 97.40% |
| 7 | 1.0874 | 91.20% | 1.2601 | 87.15% | 97.19% |
| **8** ⭐ | **1.0424** | **92.46%** | **1.2217** | **87.87%** | **97.18%** |
| 9 | 1.0039 | 93.69% | 1.2243 | 87.81% | 96.86% |
| 10 | 0.9759 | 94.40% | 1.2488 | 87.26% | 96.96% |
| 11 | 0.9490 | 95.06% | 1.2523 | 87.66% | 96.79% |
| 12 | 0.9319 | 95.64% | 1.2625 | 87.16% | 96.54% |

> ⭐ Best model saved at **Epoch 8** — Early stopping triggered at Epoch 12 (counter: 4/7)

### Evaluation Results

```
==================================================
EVALUATION RESULTS
==================================================
Top-1 Accuracy : 87.84%
Top-3 Accuracy : 95.60%
Top-5 Accuracy : 97.16%
Macro F1       : 87.73%
Weighted F1    : 87.80%
Num samples    : 14,000
Num classes    : 108
==================================================
```

**Best performing classes:**

| Class | Accuracy |
|-------|----------|
| edamame | 100.0% |
| macarons | 98.8% |
| clam_chowder | 98.0% |
| spaghetti_bolognese | 96.8% |
| miso_soup | 96.0% |

**Worst performing classes:**

| Class | Accuracy |
|-------|----------|
| pork_chop | 64.8% |
| cheesecake | 72.8% |
| hummus | 77.2% |
| garlic_bread | 78.0% |
| panna_cotta | 79.2% |

### ONNX Export Results

```
==================================================
EXPORT COMPLETE
==================================================
Model        : efficientnet_b4
Classes      : 108
ONNX path    : ./models/food_classifier.onnx
Valid        : True
Outputs match: True (max_diff < 0.00002)
Model size   : 67.6 MB
Latency mean : 23.37ms
Latency p95  : 28.41ms
Throughput   : 42.8 fps
Provider     : CPUExecutionProvider
==================================================
```

---

## 🛠️ Tech Stack

### Machine Learning
| Tool | Version | Purpose |
|------|---------|---------|
| PyTorch | 2.3.0 | Model training |
| timm | 1.0.3 | EfficientNet-B4 pretrained |
| ONNX Runtime | 1.18.0 | Fast inference serving |
| Albumentations | 1.4.8 | Data augmentation |
| scikit-learn | 1.5.0 | Evaluation metrics |

### Backend
| Tool | Version | Purpose |
|------|---------|---------|
| FastAPI | 0.111.0 | REST API framework |
| SQLAlchemy | 2.0.30 | Async ORM |
| PostgreSQL | 15 | Primary database |
| Redis | 7 | Caching |
| Google Gemini | gemini-1.5-flash | AI nutrition advice |
| SendGrid | 6.11.0 | Email service |
| Cloudinary | 1.40.0 | Image storage |
| APScheduler | 3.10.4 | Cron job scheduler |

### Frontend
| Tool | Version | Purpose |
|------|---------|---------|
| Next.js | 14.2.3 | React framework |
| TypeScript | 5.4.5 | Type safety |
| Tailwind CSS | 3.4.4 | Styling |
| Recharts | 2.12.7 | Data visualization |
| Radix UI | latest | Headless components |
| Zustand | 4.5.2 | State management |
| SWR | 2.2.5 | Data fetching |
| react-dropzone | 14.2.3 | File upload |

### Infrastructure
| Tool | Purpose |
|------|---------|
| Docker + Docker Compose | Container orchestration |
| PostgreSQL 15 | Persistent data storage |
| Redis 7 | Session cache |

---

## 🚀 Getting Started

### Prerequisites

- Docker + Docker Compose
- Python 3.10+
- Node.js 20+
- GPU (optional, for faster training)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-food-health.git
cd ai-food-health
```

### 2. Setup environment variables

```bash
cp .env.example .env
```

Fill in the required keys:

| Key | Description | Where to get |
|-----|-------------|--------------|
| `SECRET_KEY` | JWT signing key | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY` | Google Gemini API | https://aistudio.google.com |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | https://cloudinary.com |
| `CLOUDINARY_API_KEY` | Cloudinary API key | https://cloudinary.com |
| `CLOUDINARY_API_SECRET` | Cloudinary secret | https://cloudinary.com |
| `USDA_API_KEY` | Nutrition database | https://fdc.nal.usda.gov/api-guide.html |
| `SENDGRID_API_KEY` | Email service (optional) | https://sendgrid.com |

### 3. Train the ML model

```bash
cd ml

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download Food-101 dataset from Kaggle
# Extract to ml/data/raw/food-101/

# Prepare dataset (train/val split)
cd data
python3 prepare_dataset.py
cd ..

# Train EfficientNet-B4
export DATA_DIR=./data/processed
export FOOD_CLASSES_PATH=./data/food_classes.json
export ML_MODEL_PATH=./models/food_classifier.pt
export CHECKPOINT_DIR=./models/checkpoints
mkdir -p models/checkpoints

python3 training/train.py

# Resume if interrupted
python3 training/train.py --resume

# Evaluate model performance
python3 training/evaluate.py \
  --checkpoint ./models/food_classifier.pt \
  --data-dir ./data/processed \
  --output-dir ./models/eval

# Export to ONNX for serving
python3 training/export_onnx.py \
  --checkpoint ./models/food_classifier.pt \
  --output ./models/food_classifier.onnx

cd ..
```

> ⚡ Training takes approximately **35 minutes per epoch** on CPU, **5-8 minutes** on GPU.
> Best results achieved at **epoch 8** with val Top-1 accuracy of **87.87%**.

### 4. Run with Docker Compose

```bash
docker-compose up --build
```

### 5. Access the application

| Service | URL | Description |
|---------|-----|-------------|
| 🌐 Frontend | http://localhost:3000 | Main web application |
| 📡 Backend API | http://localhost:8000/docs | FastAPI Swagger UI |
| 🤖 ML Service | http://localhost:8001/docs | ML inference Swagger UI |

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create new account |
| `POST` | `/api/auth/login` | Login, receive JWT token |
| `GET` | `/api/auth/me` | Get current user profile |
| `PUT` | `/api/auth/me` | Update profile + nutrition goals |
| `DELETE` | `/api/auth/me` | Delete account |

### Food Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/food/analyze` | Upload image → food name + calories |
| `GET` | `/api/food/search?query=pho` | Search food database |
| `GET` | `/api/food/items/{id}` | Get food item details |

### Food Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/logs/` | Create food log entry |
| `GET` | `/api/logs/` | List logs (filter by date/meal) |
| `GET` | `/api/logs/daily-summary?date=2024-01-15` | Daily nutrition totals |
| `GET` | `/api/logs/weekly-summary?week_start=2024-01-15` | 7-day overview |
| `PUT` | `/api/logs/{id}` | Update serving size or note |
| `DELETE` | `/api/logs/{id}` | Delete log entry |

### AI Advice

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/advice/` | Get AI nutrition advice |
| `POST` | `/api/advice/stream` | Streaming response (SSE) |
| `GET` | `/api/advice/daily-tip` | Short daily tip |
| `GET` | `/api/advice/weekly-report` | Full weekly AI analysis |

---

## 🗺️ Development Roadmap

- [x] **Phase 1** — Project Setup (Docker, PostgreSQL, Redis, JWT auth)
- [x] **Phase 2** — ML Core (EfficientNet-B4 training, ONNX export, 87.84% accuracy)
- [x] **Phase 3** — Full Stack (FastAPI backend, Next.js frontend, Gemini AI integration)
- [ ] **Phase 4** — Production Deploy (AWS/Vercel, custom domain, SSL, monitoring)

---

## 🐛 Issues Encountered & Fixed

| Issue | Cause | Fix |
|-------|-------|-----|
| `ValueError: Input contains NaN` in evaluate | Softmax overflow with AMP | Added `.float().clamp(-50, 50)` before softmax |
| Evaluate accuracy 0% | Label index mismatch (filtered vs full classes) | Used full class list to keep indices consistent |
| `classification_report size mismatch` | Val set only had 55/108 classes | Filtered `target_names` to match present classes |
| `food-101.zip` too large for Docker | Missing `.dockerignore` | Added `.dockerignore` to exclude `data/raw/` |
| `Cannot find module '@/lib/api'` | Missing `tsconfig.json` paths config | Added `"@/*": ["./*"]` to `tsconfig.json` |
| `next.config.ts not supported` | Old Next.js version | Renamed to `next.config.mjs` |
| `Cannot find name 'float'` | Wrong TypeScript type | Replaced with `number` |
| `Types have no overlap: 'result' and 'saving'` | TypeScript narrowing in JSX block | Added `\|\| step === "saving"` to render condition |
| React 19 / lucide-react conflict | Incompatible peer dependencies | Pinned React to `18.3.1` with `--legacy-peer-deps` |
| `Could not find production build` in Docker | Volume mount overwrote `.next` build output | Removed volume mount from `docker-compose.yml` |
| Port 3000 already allocated | Process running on host | Killed existing process or changed port |

---

## 📝 License

MIT License — feel free to use this project for learning and personal projects.

---

## 👨‍💻 Author

Built with ❤️ and assisted by **Claude AI** (Anthropic).
