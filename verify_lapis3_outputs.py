"""Verifikasi artefak Lapis 3 tanpa mengubah data sumber."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lapis3_config.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    work = ROOT / config["paths"]["work_dir"]
    out = ROOT / config["paths"]["output_dir"]
    index = pd.read_csv(work / "image_index.csv")
    pairs = pd.read_csv(work / "pair_relationships.csv")
    clusters = pd.read_csv(work / "clusters.csv")
    members = pd.read_csv(work / "cluster_members.csv")
    lapis2 = pd.read_csv(ROOT / config["paths"]["lapis2_csv"], keep_default_na=False)
    if len(index) != len(lapis2):
        raise ValueError("Index Lapis 3 tidak mengikuti jumlah baris Lapis 2")
    if set(index["image_id"]) != set(lapis2["path_rel"]):
        raise ValueError("Index Lapis 3 tidak mengikuti identitas foto Lapis 2")
    pair_keys = list(zip(pairs.image_a, pairs.image_b))
    if len(pair_keys) != len(set(pair_keys)):
        raise ValueError("Pasangan relationship terduplikasi")
    if any(a == b for a, b in pair_keys):
        raise ValueError("Pasangan relationship memuat self-pair")
    if any(a > b for a, b in pair_keys):
        raise ValueError("Pasangan relationship belum canonical berdasarkan image_id")
    for field in ["embedding_similarity", "feature_match_score", "relationship_score"]:
        if field in pairs:
            values = pd.to_numeric(pairs[field], errors="coerce")
            if values.isna().any() or not values.between(0, 1).all():
                raise ValueError(f"Score di luar rentang 0-1: {field}")
    allowed_status = {"VALID", "NEED_REVIEW", "SPLIT_RECOMMENDED"}
    if not set(clusters.cluster_status).issubset(allowed_status):
        raise ValueError("Status cluster tidak dikenal")
    member_sets = members.groupby("duplicate_group_id").image_id.apply(set).to_dict()
    image_ids = set(index["image_id"])
    if not set(members.image_id).issubset(image_ids):
        raise ValueError("Cluster member tidak ada pada index Lapis 3")
    for row in clusters.to_dict("records"):
        if row["canonical_image"] not in member_sets.get(row["duplicate_group_id"], set()):
            raise ValueError("Canonical image bukan anggota cluster")
    if (work / "embeddings.npy").exists():
        embeddings = np.load(work / "embeddings.npy", mmap_mode="r")
        if embeddings.shape[0] != len(index):
            raise ValueError("Jumlah embedding tidak mengikuti index Lapis 3")
        if not np.isfinite(embeddings).all():
            raise ValueError("Embedding mengandung nilai non-finite")
        norms = np.linalg.norm(embeddings, axis=1)
        if not np.allclose(norms, 1.0, atol=1e-3):
            raise ValueError("Embedding tidak ternormalisasi L2")
    manifest_path = work / "lapis3_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if int(manifest.get("count", len(index))) != len(index):
            raise ValueError("Manifest tidak mengikuti jumlah index")
    if not pairs.empty:
        known = image_ids
        if not set(pairs.image_a).issubset(known) or not set(pairs.image_b).issubset(known):
            raise ValueError("Pair merujuk image_id di luar index Lapis 3")
        if not set(pairs.relationship_type).issubset({"EXACT_DUPLICATE", "NEAR_DUPLICATE", "SAME_CAPTURE", "SAME_OBJECT", "RELATED_ONLY", "UNRELATED"}):
            raise ValueError("Tipe relationship tidak dikenal")
    member_group_counts = members.groupby("duplicate_group_id").size()
    if any(member_group_counts < 2):
        raise ValueError("Cluster harus memiliki sedikitnya dua anggota")
    if len(clusters) != len(member_group_counts):
        raise ValueError("Ringkasan cluster tidak mengikuti cluster members")
    clustered_edges = set()
    for group_id, group in members.groupby("duplicate_group_id"):
        group_ids = set(group.image_id)
        clustered_edges.update((a, b) for a, b in pair_keys if a in group_ids and b in group_ids)
    if not clustered_edges.issubset(set(pair_keys)):
        raise ValueError("Edge cluster merujuk pair yang tidak valid")
    xlsx = out / "Hasil_Evaluasi_Lapis_3_Relasi_Duplikasi_Foto_Isolator.xlsx"
    if xlsx.exists():
        with zipfile.ZipFile(xlsx) as archive:
            if archive.testzip() is not None:
                raise ValueError("XLSX rusak")
    html = out / "Dashboard_Evaluasi_Lapis_3_Relasi_Duplikasi_Foto_Isolator.html"
    if html.exists() and "Dashboard Lapis 3" not in html.read_text(encoding="utf-8"):
        raise ValueError("Dashboard Lapis 3 tidak memiliki judul yang diharapkan")
    print(json.dumps({"images": len(index), "pairs": len(pairs), "clusters": len(clusters), "members": len(members), "status": "PASS"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
