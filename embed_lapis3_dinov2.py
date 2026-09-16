"""Lapis 3 tahap 1: DINOv2 embeddings, perceptual hashes, dan cache."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import imagehash
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = False
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lapis3_config.json"


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def require_embedding_dependencies():
    try:
        import torch
        from transformers import AutoImageProcessor, AutoModel
    except ImportError as exc:
        raise SystemExit(
            "DINOv2 belum dapat dijalankan: install torch dan transformers "
            "pada environment ini, lalu ulangi embed_lapis3_dinov2.py."
        ) from exc
    return torch, AutoImageProcessor, AutoModel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_rows(l2_path: Path) -> list[dict[str, Any]]:
    import pandas as pd

    data = pd.read_csv(l2_path, keep_default_na=False)
    required = {"ultg", "nama_file", "path_rel", "kode", "confidence"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Kolom Lapis 2 hilang: {sorted(missing)}")
    if data.path_rel.duplicated().any():
        raise ValueError("path_rel Lapis 2 tidak unik")
    rows = []
    for row in data.to_dict("records"):
        path = ROOT / row["path_rel"]
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append({
            "image_id": row["path_rel"],
            "ultg": row["ultg"],
            "nama_file": row["nama_file"],
            "path_rel": row["path_rel"],
            "kode_l1": row["kode"],
            "confidence_l1": row["confidence"],
            "image_hash": sha256(path),
            "file_size": path.stat().st_size,
        })
    return rows


def hash_row(path: Path) -> dict[str, str]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        return {
            "phash": str(imagehash.phash(rgb)),
            "dhash": str(imagehash.dhash(rgb)),
        }


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    cache = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                cache[row["image_id"]] = row
    return cache


def append_cache(path: Path, rows: list[dict[str, Any]]):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--limit", type=int, default=None, help="Batasi foto untuk smoke test")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    torch, AutoImageProcessor, AutoModel = require_embedding_dependencies()

    work = ROOT / config["paths"]["work_dir"]
    work.mkdir(parents=True, exist_ok=True)
    rows = image_rows(ROOT / config["paths"]["lapis2_csv"])
    if args.limit:
        rows = rows[:args.limit]
    cache_path = work / "embedding_cache.jsonl"
    cache = load_cache(cache_path)
    processor = AutoImageProcessor.from_pretrained(config["embedding"]["model_name"])
    model = AutoModel.from_pretrained(config["embedding"]["model_name"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()

    pending = []
    output_rows = []
    for row in rows:
        old = cache.get(row["image_id"])
        if old and old.get("image_hash") == row["image_hash"] and "embedding" in old:
            output_rows.append(old)
            continue
        path = ROOT / row["path_rel"]
        hashes = hash_row(path)
        with Image.open(path) as image:
            pending.append((row, image.convert("RGB").copy(), hashes))
        if len(pending) >= config["embedding"]["batch_size"]:
            output_rows.extend(process_batch(pending, processor, model, torch, device))
            pending = []
    if pending:
        output_rows.extend(process_batch(pending, processor, model, torch, device))

    output_rows.sort(key=lambda row: row["image_id"])
    append_cache(cache_path, output_rows)
    if not output_rows:
        raise ValueError("Tidak ada foto untuk diproses dari Lapis 2")
    missing_embeddings = [row["image_id"] for row in output_rows if "embedding" not in row]
    if missing_embeddings:
        raise ValueError(f"Cache embedding tidak lengkap: {len(missing_embeddings)} foto")
    if len({len(row["embedding"]) for row in output_rows}) != 1:
        raise ValueError("Dimensi embedding tidak konsisten")
    with (work / "image_index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["image_id", "ultg", "nama_file", "path_rel", "kode_l1", "confidence_l1", "image_hash", "file_size", "phash", "dhash", "embedding_dimension", "embedding_model"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in fields} for row in output_rows)
    embeddings = np.asarray([row["embedding"] for row in output_rows], dtype=np.float32)
    np.save(work / "embeddings.npy", embeddings)
    for row in output_rows:
        row.pop("embedding", None)
    (work / "image_index.json").write_text(json.dumps(output_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": "dinov2_embedding",
        "model": config["embedding"]["model_name"],
        "embedding_dimension": int(embeddings.shape[1]),
        "count": len(output_rows),
        "device": device,
        "input_lapis2": str(ROOT / config["paths"]["lapis2_csv"]),
        "config_sha256": sha256(args.config),
    }
    (work / "lapis3_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def process_batch(pending, processor, model, torch, device):
    images = [item[1] for item in pending]
    inputs = processor(images=images, return_tensors="pt").to(device)
    with torch.inference_mode():
        model_output = model(**inputs)
        outputs = getattr(model_output, "pooler_output", None)
        if outputs is None:
            last_hidden_state = getattr(model_output, "last_hidden_state", None)
            if last_hidden_state is None:
                raise RuntimeError("Output DINOv2 tidak memiliki pooler_output atau last_hidden_state")
            outputs = last_hidden_state[:, 0]
        outputs = torch.nn.functional.normalize(outputs, p=2, dim=1).cpu().numpy()

    result = []
    for (row, _image, hashes), vector in zip(pending, outputs):
        item = dict(row)
        item.update(hashes)
        item.update({
            "embedding": vector.tolist(),
            "embedding_dimension": int(vector.shape[0]),
            "embedding_model": "facebook/dinov2-small",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        })
        result.append(item)
    return result


if __name__ == "__main__":
    main()
