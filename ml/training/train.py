import os
import json
import time
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
import timm

import wandb
from tqdm import tqdm

from dataset import build_dataloaders

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ==========================================
# Config
# ==========================================

class TrainConfig:
    # Data
    data_dir: str = os.getenv("DATA_DIR", "./data/processed")
    classes_path: str = os.getenv("FOOD_CLASSES_PATH", "./data/food_classes.json")
    image_size: int = 224
    num_workers: int = 4

    # Model
    model_name: str = "efficientnet_b4"
    pretrained: bool = True
    dropout: float = 0.3

    # Training
    epochs: int = 30
    batch_size: int = 8
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    warmup_epochs: int = 3
    label_smoothing: float = 0.1
    grad_clip: float = 1.0
    early_stopping_patience: int = 7

    # Checkpoints
    checkpoint_dir: str = os.getenv("CHECKPOINT_DIR", "./models/checkpoints")
    best_model_path: str = os.getenv("ML_MODEL_PATH", "./models/food_classifier.pt")

    # Logging
    use_wandb: bool = os.getenv("USE_WANDB", "false").lower() == "true"
    project_name: str = "ai-food-health"
    run_name: str = f"efficientnet_b4_{time.strftime('%Y%m%d_%H%M%S')}"


cfg = TrainConfig()


# ==========================================
# Model
# ==========================================

def build_model(num_classes: int) -> nn.Module:
    model = timm.create_model(
        cfg.model_name,
        pretrained=cfg.pretrained,
        num_classes=num_classes,
        drop_rate=cfg.dropout,
    )
    logger.info(
        f"[Model] {cfg.model_name} loaded — "
        f"{sum(p.numel() for p in model.parameters()) / 1e6:.1f}M params"
    )
    return model


# ==========================================
# Training utilities
# ==========================================

class AverageMeter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0.0
        self.avg = 0.0
        self.sum = 0.0
        self.count = 0

    def update(self, val: float, n: int = 1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def accuracy(outputs: torch.Tensor, targets: torch.Tensor, topk=(1, 5)):
    with torch.no_grad():
        maxk = max(topk)
        batch_size = targets.size(0)

        _, pred = outputs.topk(maxk, dim=1, largest=True, sorted=True)
        pred = pred.t()
        correct = pred.eq(targets.view(1, -1).expand_as(pred))

        results = []
        for k in topk:
            correct_k = correct[:k].reshape(-1).float().sum()
            results.append(correct_k.mul_(100.0 / batch_size).item())
        return results


class EarlyStopping:
    def __init__(self, patience: int = 7, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score = None
        self.should_stop = False

    def __call__(self, val_acc: float) -> bool:
        if self.best_score is None:
            self.best_score = val_acc
        elif val_acc < self.best_score + self.min_delta:
            self.counter += 1
            logger.info(
                f"[EarlyStopping] No improvement — "
                f"counter: {self.counter}/{self.patience}"
            )
            if self.counter >= self.patience:
                self.should_stop = True
        else:
            self.best_score = val_acc
            self.counter = 0
        return self.should_stop


# ==========================================
# Train / val one epoch
# ==========================================

def train_one_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    epoch: int,
    scaler: torch.cuda.amp.GradScaler,
) -> dict:
    model.train()

    loss_meter = AverageMeter()
    top1_meter = AverageMeter()
    top5_meter = AverageMeter()

    pbar = tqdm(loader, desc=f"Epoch {epoch} [train]", leave=False)

    for batch_idx, (images, labels) in enumerate(pbar):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad()

        # Mixed precision forward pass
        with torch.cuda.amp.autocast(enabled=device.type == "cuda"):
            outputs = model(images)
            loss = criterion(outputs, labels)

        # Backward pass
        scaler.scale(loss).backward()

        # Gradient clipping
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)

        scaler.step(optimizer)
        scaler.update()

        top1, top5 = accuracy(outputs, labels, topk=(1, 5))
        batch_size = images.size(0)

        loss_meter.update(loss.item(), batch_size)
        top1_meter.update(top1, batch_size)
        top5_meter.update(top5, batch_size)

        pbar.set_postfix({
            "loss": f"{loss_meter.avg:.4f}",
            "top1": f"{top1_meter.avg:.2f}%",
            "top5": f"{top5_meter.avg:.2f}%",
        })

    return {
        "loss": loss_meter.avg,
        "top1": top1_meter.avg,
        "top5": top5_meter.avg,
    }


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    device: torch.device,
    epoch: int,
) -> dict:
    model.eval()

    loss_meter = AverageMeter()
    top1_meter = AverageMeter()
    top5_meter = AverageMeter()

    pbar = tqdm(loader, desc=f"Epoch {epoch} [val]", leave=False)

    for images, labels in pbar:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        with torch.cuda.amp.autocast(enabled=device.type == "cuda"):
            outputs = model(images)
            loss = criterion(outputs, labels)

        top1, top5 = accuracy(outputs, labels, topk=(1, 5))
        batch_size = images.size(0)

        loss_meter.update(loss.item(), batch_size)
        top1_meter.update(top1, batch_size)
        top5_meter.update(top5, batch_size)

        pbar.set_postfix({
            "loss": f"{loss_meter.avg:.4f}",
            "top1": f"{top1_meter.avg:.2f}%",
        })

    return {
        "loss": loss_meter.avg,
        "top1": top1_meter.avg,
        "top5": top5_meter.avg,
    }


# ==========================================
# Save / load checkpoint
# ==========================================

def save_checkpoint(
    model: nn.Module,
    optimizer: optim.Optimizer,
    epoch: int,
    metrics: dict,
    classes: list[str],
    path: str,
):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "metrics": metrics,
        "classes": classes,
        "model_name": cfg.model_name,
    }, path)
    logger.info(f"[Checkpoint] Saved to {path}")


def load_checkpoint(
    model: nn.Module,
    optimizer: optim.Optimizer,
    path: str,
    device: torch.device,
) -> tuple[int, float]:
    if not os.path.exists(path):
        return 0, 0.0

    checkpoint = torch.load(path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    epoch = checkpoint.get("epoch", 0)
    best_acc = checkpoint.get("metrics", {}).get("top1", 0.0)

    logger.info(f"[Checkpoint] Resumed from epoch {epoch}, best_acc: {best_acc:.2f}%")
    return epoch, best_acc


# ==========================================
# Main training loop
# ==========================================

def train(resume: bool = False):
    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"[Train] Using device: {device}")

    # Data
    train_loader, val_loader, classes = build_dataloaders(
        data_dir=cfg.data_dir,
        classes_path=cfg.classes_path,
        image_size=cfg.image_size,
        batch_size=cfg.batch_size,
        num_workers=cfg.num_workers,
    )
    num_classes = len(classes)

    # Model
    model = build_model(num_classes).to(device)

    # Loss with label smoothing
    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)

    # Optimizer
    optimizer = optim.AdamW(
        model.parameters(),
        lr=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
    )

    # LR scheduler — warmup then cosine annealing
    warmup_scheduler = LinearLR(
        optimizer,
        start_factor=0.1,
        end_factor=1.0,
        total_iters=cfg.warmup_epochs,
    )
    cosine_scheduler = CosineAnnealingLR(
        optimizer,
        T_max=cfg.epochs - cfg.warmup_epochs,
        eta_min=1e-6,
    )
    scheduler = SequentialLR(
        optimizer,
        schedulers=[warmup_scheduler, cosine_scheduler],
        milestones=[cfg.warmup_epochs],
    )

    # Mixed precision scaler
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == "cuda")

    # Early stopping
    early_stopping = EarlyStopping(patience=cfg.early_stopping_patience)

    # Resume from checkpoint
    start_epoch = 0
    best_acc = 0.0
    if resume:
        resume_path = os.path.join(cfg.checkpoint_dir, "last.pt")
        start_epoch, best_acc = load_checkpoint(model, optimizer, resume_path, device)

    # WandB
    if cfg.use_wandb:
        wandb.init(
            project=cfg.project_name,
            name=cfg.run_name,
            config={
                "model": cfg.model_name,
                "epochs": cfg.epochs,
                "batch_size": cfg.batch_size,
                "lr": cfg.learning_rate,
                "num_classes": num_classes,
                "image_size": cfg.image_size,
            },
        )
        wandb.watch(model, log="gradients", log_freq=100)

    # Training history
    history = []

    logger.info(f"[Train] Starting training for {cfg.epochs} epochs")
    logger.info(f"[Train] Classes: {num_classes}, Batch size: {cfg.batch_size}")

    for epoch in range(start_epoch + 1, cfg.epochs + 1):
        epoch_start = time.time()

        # Train
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, device, epoch, scaler
        )

        # Validate
        val_metrics = validate(
            model, val_loader, criterion, device, epoch
        )

        # Step scheduler
        scheduler.step()
        current_lr = optimizer.param_groups[0]["lr"]

        epoch_time = round(time.time() - epoch_start, 1)

        logger.info(
            f"[Epoch {epoch:03d}/{cfg.epochs}] "
            f"train_loss: {train_metrics['loss']:.4f} "
            f"train_top1: {train_metrics['top1']:.2f}% "
            f"val_loss: {val_metrics['loss']:.4f} "
            f"val_top1: {val_metrics['top1']:.2f}% "
            f"val_top5: {val_metrics['top5']:.2f}% "
            f"lr: {current_lr:.2e} "
            f"time: {epoch_time}s"
        )

        # Save history
        history.append({
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "train_top1": train_metrics["top1"],
            "val_loss": val_metrics["loss"],
            "val_top1": val_metrics["top1"],
            "val_top5": val_metrics["top5"],
            "lr": current_lr,
        })

        # WandB logging
        if cfg.use_wandb:
            wandb.log({
                "epoch": epoch,
                "train/loss": train_metrics["loss"],
                "train/top1": train_metrics["top1"],
                "val/loss": val_metrics["loss"],
                "val/top1": val_metrics["top1"],
                "val/top5": val_metrics["top5"],
                "lr": current_lr,
            })

        # Save last checkpoint
        save_checkpoint(
            model, optimizer, epoch, val_metrics, classes,
            path=os.path.join(cfg.checkpoint_dir, "last.pt"),
        )

        # Save best checkpoint
        if val_metrics["top1"] > best_acc:
            best_acc = val_metrics["top1"]
            save_checkpoint(
                model, optimizer, epoch, val_metrics, classes,
                path=cfg.best_model_path,
            )
            logger.info(f"[Train] New best model — val_top1: {best_acc:.2f}%")

        # Early stopping
        if early_stopping(val_metrics["top1"]):
            logger.info(f"[Train] Early stopping triggered at epoch {epoch}")
            break

    # Save training history
    history_path = os.path.join(cfg.checkpoint_dir, "history.json")
    Path(history_path).parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    logger.info(f"[Train] Training complete — best val_top1: {best_acc:.2f}%")
    logger.info(f"[Train] Best model saved at: {cfg.best_model_path}")

    if cfg.use_wandb:
        wandb.finish()

    return best_acc


# ==========================================
# Entry point
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train food classifier")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from last checkpoint",
    )
    args = parser.parse_args()
    train(resume=args.resume)