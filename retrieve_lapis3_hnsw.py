"""Lapis 3 tahap 2: HNSW approximate nearest-neighbor Top-K."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lapis3_config.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    try:
        import hnswlib
    except ImportError as exc:
        raise SystemExit(
            "HNSW belum dapat dijalankan: install hnswlib pada environment ini; "
            "jangan mengganti tahap ini dengan brute-force O(N²)."
        ) from exc

    config = json.loads(args.config.read_text(encoding="utf-8"))
    work = ROOT / config["paths"]["work_dir"]
    index_rows = json.loads((work / "image_index.json").read_text(encoding="utf-8"))
    embeddings = np.load(work / "embeddings.npy", mmap_mode="r").astype(np.float32)
    if len(index_rows) != len(embeddings):
        raise ValueError("Jumlah index dan embedding tidak sama")
    if len(index_rows) < 2:
        raise ValueError("Minimal dua gambar diperlukan")

    params = config["retrieval"]
    index = hnswlib.Index(space=params["space"], dim=embeddings.shape[1])
    index.init_index(max_elements=len(index_rows), ef_construction=params["ef_construction"], M=params["m"])
    index.add_items(embeddings, np.arange(len(index_rows)))
    index.set_ef(max(params["ef_search"], params["top_k"] + 1))
    labels, distances = index.knn_query(embeddings, k=min(params["top_k"] + 1, len(index_rows)))

    pairs = {}
    for source_i, (neighbors, dists) in enumerate(zip(labels, distances)):
        for rank, (target_i, distance) in enumerate(zip(neighbors, dists), start=1):
            if int(target_i) == source_i:
                continue
            a, b = sorted((source_i, int(target_i)))
            key = (a, b)
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            current = pairs.get(key)
            candidate = {
                "image_a": index_rows[a]["image_id"],
                "image_b": index_rows[b]["image_id"],
                "embedding_similarity": similarity,
                "rank_a_to_b": rank if source_i == a else None,
                "rank_b_to_a": rank if source_i == b else None,
            }
            if current is None:
                pairs[key] = candidate
            else:
                current["embedding_similarity"] = max(current["embedding_similarity"], similarity)
                if source_i == a:
                    current["rank_a_to_b"] = rank
                else:
                    current["rank_b_to_a"] = rank

    output = sorted(pairs.values(), key=lambda row: (-row["embedding_similarity"], row["image_a"], row["image_b"]))
    if len({(row["image_a"], row["image_b"]) for row in output}) != len(output):
        raise ValueError("Pasangan kandidat terduplikasi setelah canonicalization")
    if any(row["image_a"] >= row["image_b"] for row in output):
        raise ValueError("Pasangan kandidat tidak canonical berdasarkan image_id")
    if any(row["image_a"] == row["image_b"] for row in output):
        raise ValueError("Pasangan kandidat memuat self-neighbor")
    if any(not (0.0 <= row["embedding_similarity"] <= 1.0) for row in output):
        raise ValueError("Embedding similarity di luar rentang 0-1")
    fields = ["image_a", "image_b", "embedding_similarity", "rank_a_to_b", "rank_b_to_a"]
    with (work / "candidate_pairs.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    (work / "candidate_pairs.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"images": len(index_rows), "candidate_pairs": len(output), "top_k": params["top_k"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
