import os
import json
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from pathlib import Path
import albumentations as A
from albumentations.pytorch import ToTensorV2
import numpy as np
import logging

logger = logging.getLogger(__name__)


# ==========================================
# Load class labels
# ==========================================

def load_classes(classes_path: str) -> list[str]:
    with open(classes_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================
# Augmentation pipelines
# ==========================================

def get_train_transforms(image_size: int = 224) -> A.Compose:
    return A.Compose([
        A.RandomResizedCrop(
            height=image_size,
            width=image_size,
            scale=(0.7, 1.0),
            ratio=(0.75, 1.33),
        ),
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(
            brightness_limit=0.2,
            contrast_limit=0.2,
            p=0.5,
        ),
        A.HueSaturationValue(
            hue_shift_limit=10,
            sat_shift_limit=20,
            val_shift_limit=10,
            p=0.4,
        ),
        A.ShiftScaleRotate(
            shift_limit=0.05,
            scale_limit=0.1,
            rotate_limit=15,
            p=0.4,
        ),
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5)),
            A.MotionBlur(blur_limit=5),
            A.MedianBlur(blur_limit=3),
        ], p=0.2),
        A.CoarseDropout(
            max_holes=8,
            max_height=16,
            max_width=16,
            min_holes=1,
            p=0.2,
        ),
        A.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
        ToTensorV2(),
    ])


def get_val_transforms(image_size: int = 224) -> A.Compose:
    return A.Compose([
        A.Resize(height=int(image_size * 1.14), width=int(image_size * 1.14)),
        A.CenterCrop(height=image_size, width=image_size),
        A.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
        ToTensorV2(),
    ])


# ==========================================
# Dataset
# ==========================================

class FoodDataset(Dataset):

    def __init__(
        self,
        data_dir: str,
        classes: list[str],
        split: str = "train",
        image_size: int = 224,
        transforms: A.Compose = None,
    ):
        self.data_dir = Path(data_dir)
        self.classes = classes
        self.class_to_idx = {cls: idx for idx, cls in enumerate(classes)}
        self.split = split
        self.image_size = image_size
        self.transforms = transforms or (
            get_train_transforms(image_size)
            if split == "train"
            else get_val_transforms(image_size)
        )

        self.samples = self._load_samples()
        logger.info(
            f"[Dataset] {split} set loaded — "
            f"{len(self.samples)} samples, {len(classes)} classes"
        )

    def _load_samples(self) -> list[tuple[Path, int]]:
        samples = []
        split_dir = self.data_dir / self.split

        if not split_dir.exists():
            logger.warning(f"[Dataset] Split directory not found: {split_dir}")
            return samples

        for class_name in self.classes:
            class_dir = split_dir / class_name
            if not class_dir.exists():
                continue

            for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                for img_path in class_dir.glob(ext):
                    idx = self.class_to_idx[class_name]
                    samples.append((img_path, idx))

        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        img_path, label = self.samples[index]

        try:
            image = Image.open(img_path).convert("RGB")
            image_np = np.array(image)
            augmented = self.transforms(image=image_np)
            tensor = augmented["image"]
            return tensor, label

        except Exception as e:
            logger.error(f"[Dataset] Failed to load image {img_path}: {e}")
            # Return a blank image on error to avoid crashing the batch
            blank = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
            augmented = self.transforms(image=blank)
            return augmented["image"], label

    def get_class_weights(self) -> torch.Tensor:
        """Compute inverse frequency weights for imbalanced datasets."""
        counts = torch.zeros(len(self.classes))
        for _, label in self.samples:
            counts[label] += 1

        counts = counts.clamp(min=1)
        weights = 1.0 / counts
        weights = weights / weights.sum() * len(self.classes)
        return weights


# ==========================================
# DataLoaders factory
# ==========================================

def build_dataloaders(
    data_dir: str,
    classes_path: str,
    image_size: int = 224,
    batch_size: int = 32,
    num_workers: int = 4,
) -> tuple[DataLoader, DataLoader, list[str]]:

    classes = load_classes(classes_path)

    train_dataset = FoodDataset(
        data_dir=data_dir,
        classes=classes,
        split="train",
        image_size=image_size,
    )

    val_dataset = FoodDataset(
        data_dir=data_dir,
        classes=classes,
        split="val",
        image_size=image_size,
    )

    # Weighted sampler for imbalanced classes
    class_weights = train_dataset.get_class_weights()
    sample_weights = [
        class_weights[label].item()
        for _, label in train_dataset.samples
    ]
    sampler = torch.utils.data.WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(train_dataset),
        replacement=True,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=sampler,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    logger.info(
        f"[DataLoader] train: {len(train_loader)} batches, "
        f"val: {len(val_loader)} batches, "
        f"batch_size: {batch_size}"
    )

    return train_loader, val_loader, classes