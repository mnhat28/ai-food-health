import os
import json
import logging
import argparse
from pathlib import Path

import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    top_k_accuracy_score,
)
import timm
from tqdm import tqdm

from dataset import FoodDataset, get_val_transforms, load_classes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ==========================================
# Load model
# ==========================================

def load_model(
    checkpoint_path: str,
    device: torch.device,
) -> tuple[nn.Module, list[str]]:
    checkpoint = torch.load(checkpoint_path, map_location=device)

    classes = checkpoint["classes"]
    model_name = checkpoint.get("model_name", "efficientnet_b4")
    num_classes = len(classes)

    model = timm.create_model(
        model_name,
        pretrained=False,
        num_classes=num_classes,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    epoch = checkpoint.get("epoch", "unknown")
    metrics = checkpoint.get("metrics", {})
    logger.info(
        f"[Evaluate] Loaded checkpoint from epoch {epoch} — "
        f"val_top1: {metrics.get('top1', 'N/A'):.2f}%"
    )

    return model, classes


# ==========================================
# Run inference on val set
# ==========================================

def run_inference(
    model: nn.Module,
    data_dir: str,
    classes: list[str],
    batch_size: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Use full class list to keep label indices consistent with model output
    dataset = FoodDataset(
        data_dir=data_dir,
        classes=classes,
        split="val",
        transforms=get_val_transforms(),
    )

    if len(dataset) == 0:
        raise ValueError(f"No validation samples found in {data_dir}/val")

    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
    )

    all_labels = []
    all_preds = []
    all_probs = []

    for images, labels in tqdm(loader, desc="Running inference"):
        images = images.to(device, non_blocking=True)

        with torch.no_grad():
            outputs = model(images.to(device)).float()

        preds = outputs.argmax(dim=1)
        probs = torch.softmax(outputs, dim=1)

        all_labels.extend(labels.numpy())
        all_preds.extend(preds.cpu().numpy())
        all_probs.extend(probs.cpu().numpy())

    return (
        np.array(all_labels),
        np.array(all_preds),
        np.array(all_probs),
    )


# ==========================================
# Metrics
# ==========================================

def compute_metrics(
    labels: np.ndarray,
    preds: np.ndarray,
    probs: np.ndarray,
    classes: list[str],
) -> dict:
    # Fix NaN/Inf in probs before computing metrics
    probs = np.nan_to_num(probs, nan=0.0, posinf=1.0, neginf=0.0)
    row_sums = probs.sum(axis=1, keepdims=True).clip(min=1e-9)
    probs = probs / row_sums

    num_classes = len(classes)

    num_classes = len(classes)
    unique_labels = sorted(np.unique(labels).tolist())
    all_class_indices = list(range(num_classes))

    top1_acc = (labels == preds).mean() * 100
    top3_acc = top_k_accuracy_score(labels, probs, k=3, labels=all_class_indices) * 100
    top5_acc = top_k_accuracy_score(labels, probs, k=5, labels=all_class_indices) * 100

    unique_labels = sorted(np.unique(np.concatenate([labels, preds])))
    target_names_filtered = [classes[i] for i in unique_labels]

    report = classification_report(
        labels,
        preds,
        labels=unique_labels,
        target_names=target_names_filtered,
        output_dict=True,
        zero_division=0,
    )

    # Per-class accuracy
    per_class_acc = {}
    for idx, cls in enumerate(classes):
        mask = labels == idx
        if mask.sum() > 0:
            per_class_acc[cls] = (preds[mask] == idx).mean() * 100

    # Best and worst performing classes
    sorted_classes = sorted(per_class_acc.items(), key=lambda x: x[1])
    worst_5 = sorted_classes[:5]
    best_5 = sorted_classes[-5:][::-1]

    metrics = {
        "top1_accuracy": round(top1_acc, 2),
        "top3_accuracy": round(top3_acc, 2),
        "top5_accuracy": round(top5_acc, 2),
        "macro_f1": round(report["macro avg"]["f1-score"] * 100, 2),
        "weighted_f1": round(report["weighted avg"]["f1-score"] * 100, 2),
        "per_class_accuracy": {
            k: round(v, 2) for k, v in per_class_acc.items()
        },
        "best_5_classes": [
            {"class": cls, "accuracy": round(acc, 2)}
            for cls, acc in best_5
        ],
        "worst_5_classes": [
            {"class": cls, "accuracy": round(acc, 2)}
            for cls, acc in worst_5
        ],
        "num_samples": len(labels),
        "num_classes": len(classes),
    }

    return metrics


# ==========================================
# Visualizations
# ==========================================

def plot_confusion_matrix(
    labels: np.ndarray,
    preds: np.ndarray,
    classes: list[str],
    output_path: str,
    max_classes: int = 40,
):
    # Limit to first N classes for readability
    mask = (labels < max_classes) & (preds < max_classes)
    labels_filtered = labels[mask]
    preds_filtered = preds[mask]
    classes_filtered = classes[:max_classes]

    cm = confusion_matrix(labels_filtered, preds_filtered)
    cm_normalized = cm.astype(float) / cm.sum(axis=1, keepdims=True).clip(min=1)

    fig_size = max(16, len(classes_filtered) * 0.4)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))

    sns.heatmap(
        cm_normalized,
        annot=len(classes_filtered) <= 30,
        fmt=".2f",
        cmap="Blues",
        xticklabels=classes_filtered,
        yticklabels=classes_filtered,
        ax=ax,
        linewidths=0.5,
        cbar_kws={"label": "Normalized frequency"},
    )

    ax.set_xlabel("Predicted", fontsize=12, labelpad=10)
    ax.set_ylabel("True", fontsize=12, labelpad=10)
    ax.set_title("Confusion Matrix (Normalized)", fontsize=14, pad=15)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"[Evaluate] Confusion matrix saved to {output_path}")


def plot_per_class_accuracy(
    metrics: dict,
    output_path: str,
):
    per_class = metrics["per_class_accuracy"]
    classes = list(per_class.keys())
    accuracies = list(per_class.values())

    sorted_pairs = sorted(zip(accuracies, classes))
    accuracies_sorted, classes_sorted = zip(*sorted_pairs)

    fig_height = max(10, len(classes) * 0.25)
    fig, ax = plt.subplots(figsize=(12, fig_height))

    colors = [
        "#16a34a" if acc >= 80
        else "#eab308" if acc >= 60
        else "#ef4444"
        for acc in accuracies_sorted
    ]

    bars = ax.barh(classes_sorted, accuracies_sorted, color=colors, height=0.7)

    # Add value labels
    for bar, acc in zip(bars, accuracies_sorted):
        ax.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{acc:.1f}%",
            va="center",
            fontsize=8,
        )

    ax.set_xlabel("Accuracy (%)", fontsize=12)
    ax.set_title("Per-class Accuracy", fontsize=14)
    ax.set_xlim(0, 110)
    ax.axvline(x=80, color="#16a34a", linestyle="--", alpha=0.5, label="80% threshold")
    ax.axvline(x=60, color="#eab308", linestyle="--", alpha=0.5, label="60% threshold")
    ax.legend(fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"[Evaluate] Per-class accuracy chart saved to {output_path}")


def plot_training_history(
    history_path: str,
    output_path: str,
):
    if not os.path.exists(history_path):
        logger.warning(f"[Evaluate] History file not found: {history_path}")
        return

    with open(history_path, "r") as f:
        history = json.load(f)

    epochs = [h["epoch"] for h in history]
    train_loss = [h["train_loss"] for h in history]
    val_loss = [h["val_loss"] for h in history]
    train_top1 = [h["train_top1"] for h in history]
    val_top1 = [h["val_top1"] for h in history]
    lr = [h["lr"] for h in history]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Loss plot
    axes[0].plot(epochs, train_loss, label="Train", color="#2563eb", linewidth=2)
    axes[0].plot(epochs, val_loss, label="Val", color="#ef4444", linewidth=2)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].set_title("Training & Validation Loss")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # Accuracy plot
    axes[1].plot(epochs, train_top1, label="Train Top-1", color="#2563eb", linewidth=2)
    axes[1].plot(epochs, val_top1, label="Val Top-1", color="#ef4444", linewidth=2)
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy (%)")
    axes[1].set_title("Top-1 Accuracy")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    # LR plot
    axes[2].plot(epochs, lr, color="#16a34a", linewidth=2)
    axes[2].set_xlabel("Epoch")
    axes[2].set_ylabel("Learning Rate")
    axes[2].set_title("Learning Rate Schedule")
    axes[2].set_yscale("log")
    axes[2].grid(alpha=0.3)

    plt.suptitle("Training History", fontsize=14, y=1.02)
    plt.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"[Evaluate] Training history chart saved to {output_path}")


# ==========================================
# Main
# ==========================================

def evaluate(
    checkpoint_path: str,
    data_dir: str,
    output_dir: str,
    batch_size: int = 32,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"[Evaluate] Using device: {device}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load model
    model, classes = load_model(checkpoint_path, device)

    # Run inference using full class list to keep indices consistent
    logger.info("[Evaluate] Running inference on validation set...")
    labels, preds, probs = run_inference(
        model, data_dir, classes, batch_size, device
    )

    # Compute metrics
    logger.info("[Evaluate] Computing metrics...")
    metrics = compute_metrics(labels, preds, probs, classes)

    # Print summary
    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)
    print(f"Top-1 Accuracy : {metrics['top1_accuracy']:.2f}%")
    print(f"Top-3 Accuracy : {metrics['top3_accuracy']:.2f}%")
    print(f"Top-5 Accuracy : {metrics['top5_accuracy']:.2f}%")
    print(f"Macro F1       : {metrics['macro_f1']:.2f}%")
    print(f"Weighted F1    : {metrics['weighted_f1']:.2f}%")
    print(f"Num samples    : {metrics['num_samples']}")
    print(f"Num classes    : {metrics['num_classes']}")
    print("\nBest 5 classes:")
    for item in metrics["best_5_classes"]:
        print(f"  {item['class']:<30} {item['accuracy']:.1f}%")
    print("\nWorst 5 classes:")
    for item in metrics["worst_5_classes"]:
        print(f"  {item['class']:<30} {item['accuracy']:.1f}%")
    print("=" * 50 + "\n")

    # Save metrics JSON
    metrics_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"[Evaluate] Metrics saved to {metrics_path}")

    # Save visualizations
    plot_confusion_matrix(
        labels, preds, classes,
        output_path=os.path.join(output_dir, "confusion_matrix.png"),
    )

    plot_per_class_accuracy(
        metrics,
        output_path=os.path.join(output_dir, "per_class_accuracy.png"),
    )

    history_path = os.path.join(
        os.path.dirname(checkpoint_path), "history.json"
    )
    plot_training_history(
        history_path=history_path,
        output_path=os.path.join(output_dir, "training_history.png"),
    )

    return metrics


# ==========================================
# Entry point
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate food classifier")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="./models/food_classifier.pt",
        help="Path to model checkpoint",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data/processed",
        help="Path to dataset directory",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models/eval",
        help="Directory to save evaluation results",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
    )
    args = parser.parse_args()

    evaluate(
        checkpoint_path=args.checkpoint,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
    )