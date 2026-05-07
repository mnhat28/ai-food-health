import os
import json
import logging
import argparse
from pathlib import Path

import torch
import torch.nn as nn
import numpy as np
import timm
import onnx
import onnxruntime as ort
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ==========================================
# Load PyTorch model
# ==========================================

def load_pytorch_model(
    checkpoint_path: str,
    device: torch.device,
) -> tuple[nn.Module, list[str], str]:
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

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
        f"[Export] Loaded checkpoint — "
        f"epoch: {epoch}, "
        f"val_top1: {metrics.get('top1', 'N/A')}"
    )
    logger.info(f"[Export] Model: {model_name}, Classes: {num_classes}")

    return model, classes, model_name


# ==========================================
# Export to ONNX
# ==========================================

def export_to_onnx(
    model: nn.Module,
    output_path: str,
    image_size: int = 224,
    opset_version: int = 17,
    dynamic_batch: bool = True,
) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Dummy input for tracing
    dummy_input = torch.randn(1, 3, image_size, image_size)

    dynamic_axes = None
    if dynamic_batch:
        dynamic_axes = {
            "input": {0: "batch_size"},
            "output": {0: "batch_size"},
        }

    logger.info(f"[Export] Exporting to ONNX — opset: {opset_version}")

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes=dynamic_axes,
        verbose=False,
    )

    logger.info(f"[Export] ONNX model saved to {output_path}")
    return output_path


# ==========================================
# Validate ONNX model
# ==========================================

def validate_onnx(onnx_path: str) -> bool:
    logger.info("[Export] Validating ONNX model structure...")
    try:
        model = onnx.load(onnx_path)
        onnx.checker.check_model(model)
        logger.info("[Export] ONNX model structure is valid")

        # Log model info
        input_shape = [
            d.dim_value
            for d in model.graph.input[0].type.tensor_type.shape.dim
        ]
        output_shape = [
            d.dim_value
            for d in model.graph.output[0].type.tensor_type.shape.dim
        ]
        logger.info(f"[Export] Input shape: {input_shape}")
        logger.info(f"[Export] Output shape: {output_shape}")

        file_size_mb = os.path.getsize(onnx_path) / (1024 * 1024)
        logger.info(f"[Export] Model size: {file_size_mb:.1f} MB")

        return True

    except Exception as e:
        logger.error(f"[Export] ONNX validation failed: {e}")
        return False


# ==========================================
# Benchmark inference speed
# ==========================================

def benchmark_inference(
    onnx_path: str,
    image_size: int = 224,
    num_runs: int = 100,
    warmup_runs: int = 10,
) -> dict:
    import time

    providers = (
        ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if ort.get_device() == "GPU"
        else ["CPUExecutionProvider"]
    )

    session = ort.InferenceSession(onnx_path, providers=providers)
    input_name = session.get_inputs()[0].name

    dummy = np.random.randn(1, 3, image_size, image_size).astype(np.float32)

    # Warmup
    for _ in range(warmup_runs):
        session.run(None, {input_name: dummy})

    # Benchmark
    times = []
    for _ in range(num_runs):
        start = time.perf_counter()
        session.run(None, {input_name: dummy})
        times.append((time.perf_counter() - start) * 1000)

    times = np.array(times)
    results = {
        "mean_ms": round(float(times.mean()), 2),
        "std_ms": round(float(times.std()), 2),
        "min_ms": round(float(times.min()), 2),
        "max_ms": round(float(times.max()), 2),
        "p50_ms": round(float(np.percentile(times, 50)), 2),
        "p95_ms": round(float(np.percentile(times, 95)), 2),
        "p99_ms": round(float(np.percentile(times, 99)), 2),
        "throughput_fps": round(1000 / float(times.mean()), 1),
        "provider": providers[0],
        "num_runs": num_runs,
    }

    logger.info(
        f"[Export] Inference benchmark — "
        f"mean: {results['mean_ms']}ms, "
        f"p95: {results['p95_ms']}ms, "
        f"throughput: {results['throughput_fps']} fps"
    )

    return results


# ==========================================
# Compare PyTorch vs ONNX outputs
# ==========================================

def compare_outputs(
    pytorch_model: nn.Module,
    onnx_path: str,
    image_size: int = 224,
    num_samples: int = 5,
    tolerance: float = 1e-4,
) -> bool:
    logger.info("[Export] Comparing PyTorch vs ONNX outputs...")

    session = ort.InferenceSession(
        onnx_path,
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name

    all_match = True

    for i in range(num_samples):
        dummy = torch.randn(1, 3, image_size, image_size)

        # PyTorch inference
        with torch.no_grad():
            pt_output = pytorch_model(dummy).numpy()

        # ONNX inference
        onnx_output = session.run(None, {input_name: dummy.numpy()})[0]

        max_diff = np.abs(pt_output - onnx_output).max()
        match = max_diff < tolerance

        if not match:
            all_match = False
            logger.warning(
                f"[Export] Sample {i + 1}: outputs differ — max_diff: {max_diff:.6f}"
            )
        else:
            logger.info(
                f"[Export] Sample {i + 1}: outputs match — max_diff: {max_diff:.6f}"
            )

    if all_match:
        logger.info("[Export] PyTorch and ONNX outputs match within tolerance")
    else:
        logger.warning("[Export] Some outputs differ — check model export settings")

    return all_match


# ==========================================
# Save model metadata
# ==========================================

def save_metadata(
    output_dir: str,
    classes: list[str],
    model_name: str,
    onnx_path: str,
    image_size: int,
    benchmark: dict,
    export_config: dict,
):
    metadata = {
        "model_name": model_name,
        "onnx_path": onnx_path,
        "num_classes": len(classes),
        "classes": classes,
        "image_size": image_size,
        "input_shape": [1, 3, image_size, image_size],
        "preprocessing": {
            "resize": image_size,
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
            "channel_order": "RGB",
        },
        "benchmark": benchmark,
        "export_config": export_config,
    }

    metadata_path = os.path.join(output_dir, "model_metadata.json")
    Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"[Export] Metadata saved to {metadata_path}")
    return metadata


# ==========================================
# Main export pipeline
# ==========================================

def export(
    checkpoint_path: str,
    output_path: str,
    image_size: int = 224,
    opset_version: int = 17,
    dynamic_batch: bool = True,
    run_benchmark: bool = True,
    num_benchmark_runs: int = 100,
):
    device = torch.device("cpu")
    logger.info("[Export] Starting ONNX export pipeline")

    # Step 1 — Load PyTorch model
    logger.info("[Export] Step 1/5 — Loading PyTorch checkpoint")
    model, classes, model_name = load_pytorch_model(checkpoint_path, device)

    # Step 2 — Export to ONNX
    logger.info("[Export] Step 2/5 — Exporting to ONNX")
    export_to_onnx(
        model=model,
        output_path=output_path,
        image_size=image_size,
        opset_version=opset_version,
        dynamic_batch=dynamic_batch,
    )

    # Step 3 — Validate ONNX
    logger.info("[Export] Step 3/5 — Validating ONNX model")
    is_valid = validate_onnx(output_path)
    if not is_valid:
        raise RuntimeError("ONNX validation failed — check export settings")

    # Step 4 — Compare outputs
    logger.info("[Export] Step 4/5 — Comparing PyTorch vs ONNX outputs")
    outputs_match = compare_outputs(
        pytorch_model=model,
        onnx_path=output_path,
        image_size=image_size,
    )
    if not outputs_match:
        logger.warning("[Export] Output mismatch detected — proceed with caution")

    # Step 5 — Benchmark
    benchmark = {}
    if run_benchmark:
        logger.info("[Export] Step 5/5 — Benchmarking inference speed")
        benchmark = benchmark_inference(
            onnx_path=output_path,
            image_size=image_size,
            num_runs=num_benchmark_runs,
        )
    else:
        logger.info("[Export] Step 5/5 — Skipping benchmark")

    # Save metadata
    output_dir = str(Path(output_path).parent)
    export_config = {
        "opset_version": opset_version,
        "dynamic_batch": dynamic_batch,
        "image_size": image_size,
        "source_checkpoint": checkpoint_path,
    }
    metadata = save_metadata(
        output_dir=output_dir,
        classes=classes,
        model_name=model_name,
        onnx_path=output_path,
        image_size=image_size,
        benchmark=benchmark,
        export_config=export_config,
    )

    # Print summary
    print("\n" + "=" * 50)
    print("EXPORT COMPLETE")
    print("=" * 50)
    print(f"Model        : {model_name}")
    print(f"Classes      : {len(classes)}")
    print(f"ONNX path    : {output_path}")
    print(f"Valid        : {is_valid}")
    print(f"Outputs match: {outputs_match}")
    if benchmark:
        print(f"Latency mean : {benchmark['mean_ms']}ms")
        print(f"Latency p95  : {benchmark['p95_ms']}ms")
        print(f"Throughput   : {benchmark['throughput_fps']} fps")
    print("=" * 50 + "\n")

    return metadata


# ==========================================
# Entry point
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export food classifier to ONNX")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="./models/food_classifier.pt",
        help="Path to PyTorch checkpoint",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./models/food_classifier.onnx",
        help="Output path for ONNX model",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=224,
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset version",
    )
    parser.add_argument(
        "--no-dynamic-batch",
        action="store_true",
        help="Disable dynamic batch size",
    )
    parser.add_argument(
        "--no-benchmark",
        action="store_true",
        help="Skip inference benchmark",
    )
    parser.add_argument(
        "--benchmark-runs",
        type=int,
        default=100,
    )
    args = parser.parse_args()

    export(
        checkpoint_path=args.checkpoint,
        output_path=args.output,
        image_size=args.image_size,
        opset_version=args.opset,
        dynamic_batch=not args.no_dynamic_batch,
        run_benchmark=not args.no_benchmark,
        num_benchmark_runs=args.benchmark_runs,
    )