#!/bin/bash

# ==========================================
# AI Food Health — ML Setup Script
# ==========================================

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging helpers
log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
log_step()    { echo -e "\n${GREEN}========================================${NC}"; echo -e "${GREEN} $1${NC}"; echo -e "${GREEN}========================================${NC}"; }


# ==========================================
# Check prerequisites
# ==========================================

check_prerequisites() {
    log_step "Step 0 — Checking prerequisites"

    # Python
    if ! command -v python3 &>/dev/null; then
        log_error "python3 not found. Install with: sudo apt install python3"
    fi
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_success "Python $PYTHON_VERSION found"

    # pip
    if ! command -v pip3 &>/dev/null; then
        log_error "pip3 not found. Install with: sudo apt install python3-pip"
    fi
    log_success "pip3 found"

    # Check we are in the ml/ directory
    if [ ! -f "requirements.txt" ]; then
        log_error "Please run this script from the ml/ directory: cd ml && bash setup.sh"
    fi
    log_success "Running from correct directory: $(pwd)"
}


# ==========================================
# Setup virtual environment
# ==========================================

setup_venv() {
    log_step "Step 1 — Setting up virtual environment"

    if [ -d "venv" ]; then
        log_warning "venv already exists — skipping creation"
    else
        python3 -m venv venv
        log_success "Virtual environment created"
    fi

    source venv/bin/activate
    log_success "Virtual environment activated"

    pip install --upgrade pip --quiet
    log_success "pip upgraded"
}


# ==========================================
# Install dependencies
# ==========================================

install_dependencies() {
    log_step "Step 2 — Installing dependencies"

    log_info "This may take 5-10 minutes (PyTorch is large)..."

    pip install -r requirements.txt \
        --quiet \
        --no-cache-dir

    log_success "All dependencies installed"

    # Install icrawler for Vietnamese food scraping
    pip install icrawler --quiet
    log_success "icrawler installed"
}


# ==========================================
# Check dataset structure
# ==========================================

check_dataset() {
    log_step "Step 3 — Checking dataset structure"

    # Try to find food-101 in common locations
    FOOD101_DIR=""

    CANDIDATES=(
        "data/raw/food-101"
        "data/raw/food101"
        "data/raw/Food-101"
        "data/raw"
    )

    for candidate in "${CANDIDATES[@]}"; do
        if [ -d "$candidate/images" ]; then
            FOOD101_DIR="$candidate"
            break
        fi
    done

    if [ -z "$FOOD101_DIR" ]; then
        log_warning "Food-101 dataset not found in expected locations"
        log_info "Expected structure:"
        echo "    ml/data/raw/food-101/"
        echo "    ml/data/raw/food-101/images/"
        echo "    ml/data/raw/food-101/meta/"
        echo ""
        log_info "Please make sure Food-101 is extracted to ml/data/raw/food-101/"
        read -p "Press Enter when ready, or Ctrl+C to exit..."
    else
        CLASS_COUNT=$(ls "$FOOD101_DIR/images/" | wc -l)
        log_success "Food-101 found at: $FOOD101_DIR ($CLASS_COUNT classes)"
    fi

    # Count images
    if [ -d "$FOOD101_DIR/images" ]; then
        TOTAL_IMAGES=$(find "$FOOD101_DIR/images" -name "*.jpg" | wc -l)
        log_info "Total images: $TOTAL_IMAGES"
    fi
}


# ==========================================
# Download Vietnamese food images
# ==========================================

download_vietnamese_food() {
    log_step "Step 4 — Downloading Vietnamese food images"

    VIET_DIR="data/raw/vietnamese"

    # Check if already downloaded
    EXISTING=$(find "$VIET_DIR" -name "*.jpg" 2>/dev/null | wc -l)
    if [ "$EXISTING" -gt 500 ]; then
        log_warning "Vietnamese food images already exist ($EXISTING images) — skipping"
        return
    fi

    log_info "Downloading Vietnamese food images via icrawler..."
    log_info "This may take 10-20 minutes depending on internet speed..."

    python3 - <<'PYEOF'
import os
import sys

try:
    from icrawler.builtin import GoogleImageCrawler
except ImportError:
    print("icrawler not found — skipping Vietnamese food download")
    sys.exit(0)

foods = {
    "pho_bo":          "phở bò việt nam",
    "banh_mi":         "bánh mì việt nam",
    "com_tam":         "cơm tấm sườn bì chả",
    "bun_bo_hue":      "bún bò huế",
    "goi_cuon":        "gỏi cuốn việt nam",
    "banh_xeo":        "bánh xèo việt nam",
    "bun_thit_nuong":  "bún thịt nướng việt nam",
    "ca_kho_to":       "cá kho tộ việt nam",
    "canh_chua":       "canh chua việt nam",
    "com_chien":       "cơm chiên việt nam",
    "bun_cha":         "bún chả hà nội",
    "hu_tieu":         "hủ tiếu nam vang",
    "mi_quang":        "mì quảng đà nẵng",
    "pho_ga":          "phở gà việt nam",
    "thit_kho_trung":  "thịt kho trứng việt nam",
    "cha_gio":         "chả giò việt nam",
    "banh_cuon":       "bánh cuốn việt nam",
    "cao_lau":         "cao lầu hội an",
    "bun_rieu":        "bún riêu cua việt nam",
    "xoi_gac":         "xôi gấc việt nam",
}

total = 0
for folder, keyword in foods.items():
    out_dir = f"./data/raw/vietnamese/{folder}"
    os.makedirs(out_dir, exist_ok=True)

    existing = len([f for f in os.listdir(out_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
    if existing >= 100:
        print(f"  [SKIP] {folder} — already has {existing} images")
        total += existing
        continue

    print(f"  [DOWN] {folder} — '{keyword}'")
    try:
        crawler = GoogleImageCrawler(
            storage={"root_dir": out_dir},
            log_level=50,  # Suppress logs
        )
        crawler.crawl(keyword=keyword, max_num=150)
        count = len([f for f in os.listdir(out_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        print(f"  [OK]   {folder} — {count} images downloaded")
        total += count
    except Exception as e:
        print(f"  [FAIL] {folder} — {e}")

print(f"\nTotal Vietnamese food images: {total}")
PYEOF

    VIET_COUNT=$(find "$VIET_DIR" -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" 2>/dev/null | wc -l)
    log_success "Vietnamese food images ready: $VIET_COUNT images"
}


# ==========================================
# Prepare dataset
# ==========================================

prepare_dataset() {
    log_step "Step 5 — Preparing dataset"

    PROCESSED_DIR="data/processed"

    # Check if already prepared
    if [ -d "$PROCESSED_DIR/train" ] && [ -d "$PROCESSED_DIR/val" ]; then
        TRAIN_COUNT=$(find "$PROCESSED_DIR/train" -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" 2>/dev/null | wc -l)
        VAL_COUNT=$(find "$PROCESSED_DIR/val" -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" 2>/dev/null | wc -l)

        if [ "$TRAIN_COUNT" -gt 1000 ]; then
            log_warning "Dataset already prepared (train: $TRAIN_COUNT, val: $VAL_COUNT) — skipping"
            return
        fi
    fi

    log_info "Running prepare_dataset.py..."
    cd data
    python3 prepare_dataset.py
    cd ..

    TRAIN_COUNT=$(find "$PROCESSED_DIR/train" -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" 2>/dev/null | wc -l)
    VAL_COUNT=$(find "$PROCESSED_DIR/val" -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" 2>/dev/null | wc -l)
    log_success "Dataset prepared — train: $TRAIN_COUNT, val: $VAL_COUNT"
}


# ==========================================
# Train model
# ==========================================

train_model() {
    log_step "Step 6 — Training model"

    BEST_MODEL="models/food_classifier.pt"

    if [ -f "$BEST_MODEL" ]; then
        log_warning "Model already exists at $BEST_MODEL"
        read -p "Retrain from scratch? (y/N): " retrain
        if [[ ! "$retrain" =~ ^[Yy]$ ]]; then
            log_info "Skipping training"
            return
        fi
    fi

    mkdir -p models/checkpoints

    export DATA_DIR=./data/processed
    export FOOD_CLASSES_PATH=./data/food_classes.json
    export ML_MODEL_PATH=./models/food_classifier.pt
    export CHECKPOINT_DIR=./models/checkpoints

    log_info "Starting training — this will take a while..."
    log_info "You can monitor progress in the terminal"

    # Check if resuming
    if [ -f "models/checkpoints/last.pt" ]; then
        log_info "Found existing checkpoint — resuming training"
        python3 training/train.py --resume
    else
        python3 training/train.py
    fi

    if [ -f "$BEST_MODEL" ]; then
        log_success "Training complete — model saved at $BEST_MODEL"
    else
        log_error "Training failed — model file not found"
    fi
}


# ==========================================
# Evaluate model
# ==========================================

evaluate_model() {
    log_step "Step 7 — Evaluating model"

    BEST_MODEL="models/food_classifier.pt"

    if [ ! -f "$BEST_MODEL" ]; then
        log_warning "No model found — skipping evaluation"
        return
    fi

    mkdir -p models/eval

    python3 training/evaluate.py \
        --checkpoint "$BEST_MODEL" \
        --data-dir ./data/processed \
        --output-dir ./models/eval

    log_success "Evaluation complete — results saved to models/eval/"
}


# ==========================================
# Export ONNX
# ==========================================

export_onnx() {
    log_step "Step 8 — Exporting to ONNX"

    BEST_MODEL="models/food_classifier.pt"
    ONNX_MODEL="models/food_classifier.onnx"

    if [ ! -f "$BEST_MODEL" ]; then
        log_warning "No PyTorch model found — skipping ONNX export"
        return
    fi

    if [ -f "$ONNX_MODEL" ]; then
        log_warning "ONNX model already exists at $ONNX_MODEL"
        read -p "Re-export? (y/N): " reexport
        if [[ ! "$reexport" =~ ^[Yy]$ ]]; then
            log_info "Skipping ONNX export"
            return
        fi
    fi

    python3 training/export_onnx.py \
        --checkpoint "$BEST_MODEL" \
        --output "$ONNX_MODEL"

    if [ -f "$ONNX_MODEL" ]; then
        ONNX_SIZE=$(du -sh "$ONNX_MODEL" | cut -f1)
        log_success "ONNX export complete — $ONNX_MODEL ($ONNX_SIZE)"
    else
        log_error "ONNX export failed"
    fi
}


# ==========================================
# Final summary
# ==========================================

print_summary() {
    log_step "Setup Complete"

    echo ""
    echo -e "${GREEN}Files ready:${NC}"

    check_file() {
        if [ -f "$1" ]; then
            echo -e "  ${GREEN}✓${NC} $1"
        else
            echo -e "  ${RED}✗${NC} $1 (missing)"
        fi
    }

    check_file "models/food_classifier.pt"
    check_file "models/food_classifier.onnx"
    check_file "models/model_metadata.json"
    check_file "models/eval/metrics.json"

    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Go back to project root:  cd .."
    echo "  2. Start all services:       docker-compose up --build"
    echo "  3. Open browser:             http://localhost:3000"
    echo ""
}


# ==========================================
# Menu
# ==========================================

show_menu() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   AI Food Health — ML Setup           ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "  1) Run full setup (recommended)"
    echo "  2) Setup venv + install dependencies only"
    echo "  3) Prepare dataset only"
    echo "  4) Train model only"
    echo "  5) Evaluate model only"
    echo "  6) Export ONNX only"
    echo "  7) Exit"
    echo ""
    read -p "Choose an option [1-7]: " choice
}


# ==========================================
# Entry point
# ==========================================

main() {
    # If argument passed, run directly
    if [ "$1" == "--full" ]; then
        check_prerequisites
        setup_venv
        install_dependencies
        check_dataset
        download_vietnamese_food
        prepare_dataset
        train_model
        evaluate_model
        export_onnx
        print_summary
        exit 0
    fi

    show_menu

    case $choice in
        1)
            check_prerequisites
            setup_venv
            install_dependencies
            check_dataset
            download_vietnamese_food
            prepare_dataset
            train_model
            evaluate_model
            export_onnx
            print_summary
            ;;
        2)
            check_prerequisites
            setup_venv
            install_dependencies
            ;;
        3)
            source venv/bin/activate 2>/dev/null || true
            check_dataset
            download_vietnamese_food
            prepare_dataset
            ;;
        4)
            source venv/bin/activate 2>/dev/null || true
            train_model
            ;;
        5)
            source venv/bin/activate 2>/dev/null || true
            evaluate_model
            ;;
        6)
            source venv/bin/activate 2>/dev/null || true
            export_onnx
            ;;
        7)
            echo "Bye!"
            exit 0
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac
}

main "$@"