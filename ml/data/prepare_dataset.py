import os
import json
import shutil
import random
from pathlib import Path
from tqdm import tqdm

# ==========================================
# Config
# ==========================================

RAW_DIR = Path("./raw/food-101")
OUTPUT_DIR = Path("./processed")
CLASSES_PATH = Path("./food_classes.json")
TRAIN_RATIO = 0.85
SEED = 42

random.seed(SEED)


# ==========================================
# Load class list
# ==========================================

def load_classes() -> list[str]:
    with open(CLASSES_PATH, "r") as f:
        return json.load(f)


# ==========================================
# Map Food-101 labels to our labels
# ==========================================

FOOD101_TO_OURS = {
    "bibimbap": "bibimbap",
    "bruschetta": "bruschetta",
    "caesar_salad": "caesar_salad",
    "cheesecake": "cheesecake",
    "chicken_curry": "chicken_curry",
    "chicken_wings": "chicken_wings",
    "chocolate_cake": "chocolate_cake",
    "churros": "churros",
    "clam_chowder": "clam_chowder",
    "club_sandwich": "club_sandwich",
    "creme_brulee": "creme_brulee",
    "donuts": "donuts",
    "dumplings": "dumplings",
    "edamame": "edamame",
    "eggs_benedict": "eggs_benedict",
    "falafel": "falafel",
    "fish_and_chips": "fish_and_chips",
    "french_fries": "french_fries",
    "french_onion_soup": "french_onion_soup",
    "french_toast": "french_toast",
    "frozen_yogurt": "frozen_yogurt",
    "garlic_bread": "garlic_bread",
    "greek_salad": "greek_salad",
    "grilled_salmon": "grilled_salmon",
    "gyoza": "gyoza",
    "hamburger": "hamburger",
    "hot_dog": "hot_dog",
    "hummus": "hummus",
    "ice_cream": "ice_cream",
    "lasagna": "lasagna",
    "lobster_roll_salad": "lobster_roll",
    "macaroni_and_cheese": "macaroni_and_cheese",
    "macarons": "macarons",
    "miso_soup": "miso_soup",
    "mushroom_risotto": "mushroom_risotto",
    "nachos": "nachos",
    "onion_rings": "onion_rings",
    "oysters": "oysters",
    "pad_thai": "pad_thai",
    "paella": "paella",
    "pancakes": "pancakes",
    "panna_cotta": "panna_cotta",
    "peking_duck": "peking_duck",
    "pizza": "pizza",
    "pork_chop": "pork_chop",
    "pulled_pork_sandwich": "pulled_pork_sandwich",
    "ramen": "ramen",
    "red_velvet_cake": "red_velvet_cake",
    "samosa": "samosa",
    "seaweed_salad": "greek_salad",
    "shrimp_scampi": "shrimp_scampi",
    "spaghetti_bolognese": "spaghetti_bolognese",
    "spring_rolls": "spring_rolls",
    "steak": "steak",
    "strawberry_shortcake": "strawberry_shortcake",
    "sushi": "sushi",
    "tacos": "tacos",
    "tiramisu": "tiramisu",
    "waffles": "waffles",
}


# ==========================================
# Copy images
# ==========================================

def copy_images(
    src_dir: Path,
    dst_dir: Path,
    images: list[str],
    label: str,
):
    dst_class_dir = dst_dir / label
    dst_class_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for img_name in images:
        src = src_dir / img_name
        if src.exists():
            dst = dst_class_dir / src.name
            shutil.copy2(src, dst)
            copied += 1

    return copied


# ==========================================
# Process Food-101
# ==========================================

def process_food101(classes: list[str]):
    images_dir = RAW_DIR / "images"
    meta_dir = RAW_DIR / "meta"

    if not images_dir.exists():
        print(f"[Error] Food-101 images not found at {images_dir}")
        print("Please download Food-101 dataset first")
        return 0

    # Load official train/test split if available
    train_json = meta_dir / "train.json"
    test_json = meta_dir / "test.json"

    if train_json.exists() and test_json.exists():
        print("[Info] Using official Food-101 train/test split")
        with open(train_json) as f:
            official_train = json.load(f)
        with open(test_json) as f:
            official_test = json.load(f)
    else:
        official_train = None
        official_test = None

    total_copied = 0
    our_classes_set = set(classes)

    for food101_label, our_label in tqdm(FOOD101_TO_OURS.items(), desc="Processing Food-101"):
        if our_label not in our_classes_set:
            continue

        src_class_dir = images_dir / food101_label
        if not src_class_dir.exists():
            print(f"[Warning] Class not found: {food101_label}")
            continue

        all_images = list(src_class_dir.glob("*.jpg"))
        all_names = [img.name for img in all_images]

        if official_train and food101_label in official_train:
            train_names = [
                Path(p).name + ".jpg"
                for p in official_train[food101_label]
            ]
            test_names = [
                Path(p).name + ".jpg"
                for p in official_test.get(food101_label, [])
            ]
        else:
            random.shuffle(all_names)
            split_idx = int(len(all_names) * TRAIN_RATIO)
            train_names = all_names[:split_idx]
            test_names = all_names[split_idx:]

        # Copy to processed
        train_copied = copy_images(
            src_class_dir,
            OUTPUT_DIR / "train",
            train_names,
            our_label,
        )
        val_copied = copy_images(
            src_class_dir,
            OUTPUT_DIR / "val",
            test_names,
            our_label,
        )

        total_copied += train_copied + val_copied

    return total_copied


# ==========================================
# Process Vietnamese food
# ==========================================

def process_vietnamese_food(classes: list[str]):
    viet_dir = RAW_DIR / "vietnamese"

    if not viet_dir.exists():
        print(f"[Warning] Vietnamese food directory not found: {viet_dir}")
        print("[Info] Skipping Vietnamese food — add images manually to:")
        print(f"       {viet_dir}/<class_name>/*.jpg")
        return 0

    viet_classes = [
        "banh_mi", "banh_xeo", "bo_luc_lac", "bun_bo_hue",
        "bun_cha", "bun_thit_nuong", "ca_kho_to", "canh_chua",
        "cao_lau", "che_ba_mau", "com_chien", "com_tam",
        "goi_cuon", "hu_tieu", "mi_quang", "pho_bo",
        "pho_ga", "thit_kho_trung", "xoi_gac", "banh_cuon",
        "banh_beo", "banh_trang_nuong", "bun_mam", "cha_gio",
        "chao_long", "com_hen", "com_nieu", "dau_hu_sot_ca",
        "ga_nuong", "lau_thai", "nem_cuon", "rau_muong_xao",
        "suon_nuong", "thit_heo_quay", "bun_rieu",
    ]

    total_copied = 0
    classes_set = set(classes)

    for cls in tqdm(viet_classes, desc="Processing Vietnamese food"):
        if cls not in classes_set:
            continue

        src_dir = viet_dir / cls
        if not src_dir.exists():
            continue

        all_images = [f.name for f in src_dir.glob("*.jpg")]
        all_images += [f.name for f in src_dir.glob("*.jpeg")]
        all_images += [f.name for f in src_dir.glob("*.png")]

        if not all_images:
            continue

        random.shuffle(all_images)
        split_idx = int(len(all_images) * TRAIN_RATIO)
        train_imgs = all_images[:split_idx]
        val_imgs = all_images[split_idx:]

        train_copied = copy_images(src_dir, OUTPUT_DIR / "train", train_imgs, cls)
        val_copied = copy_images(src_dir, OUTPUT_DIR / "val", val_imgs, cls)
        total_copied += train_copied + val_copied

    return total_copied


# ==========================================
# Print dataset stats
# ==========================================

def print_stats():
    print("\n" + "=" * 50)
    print("DATASET STATISTICS")
    print("=" * 50)

    for split in ["train", "val"]:
        split_dir = OUTPUT_DIR / split
        if not split_dir.exists():
            continue

        total = 0
        class_counts = {}

        for class_dir in sorted(split_dir.iterdir()):
            if class_dir.is_dir():
                count = len(list(class_dir.glob("*")))
                class_counts[class_dir.name] = count
                total += count

        print(f"\n{split.upper()} SET — {total} images, {len(class_counts)} classes")
        print(f"  Min per class : {min(class_counts.values())}")
        print(f"  Max per class : {max(class_counts.values())}")
        print(f"  Avg per class : {total // len(class_counts)}")

    print("=" * 50 + "\n")


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":
    print("[Prepare] Starting dataset preparation...")

    classes = load_classes()
    print(f"[Prepare] Target classes: {len(classes)}")

    # Create output directories
    (OUTPUT_DIR / "train").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "val").mkdir(parents=True, exist_ok=True)

    # Process Food-101
    print("\n[Prepare] Processing Food-101...")
    food101_count = process_food101(classes)
    print(f"[Prepare] Food-101: {food101_count} images copied")

    # Process Vietnamese food
    print("\n[Prepare] Processing Vietnamese food...")
    viet_count = process_vietnamese_food(classes)
    print(f"[Prepare] Vietnamese food: {viet_count} images copied")

    # Print stats
    print_stats()

    print("[Prepare] Dataset preparation complete!")
    print(f"[Prepare] Output directory: {OUTPUT_DIR.resolve()}")