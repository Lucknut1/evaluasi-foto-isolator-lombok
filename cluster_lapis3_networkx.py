"""Lapis 3 tahap 5-6: NetworkX clusters dan cluster validation."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lapis3_config.json"


def quality_score(row):
    score = 0
    score += 100 if row.get("kode_l1") == "S" else 0
    score -= 30 if row.get("kode_l1") == "B" else 0
    score -= 25 if row.get("kode_l1") == "P" else 0
    score -= 20 if row.get("kode_l1") == "J" else 0
    score -= 20 if row.get("kode_l1") == "H" else 0
    score += min(20, int(row.get("file_size") or 0) / 100000)
    return round(score, 3)


def status_for(avg_sim, min_sim, diameter, strong_ratio, cfg):
    if min_sim < cfg["split_minimum_similarity"]:
        return "SPLIT_RECOMMENDED", "minimum_similarity_too_low"
    if diameter > cfg["max_diameter"]:
        return "SPLIT_RECOMMENDED", "cluster_diameter_high"
    if avg_sim >= cfg["valid_average_similarity"] and min_sim >= cfg["valid_minimum_similarity"] and strong_ratio >= cfg["min_strong_edge_ratio"]:
        return "VALID", "internal_similarity_consistent"
    return "NEED_REVIEW", "borderline_similarity_or_weak_edge_ratio"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    work = ROOT / config["paths"]["work_dir"]
    index_rows = json.loads((work / "image_index.json").read_text(encoding="utf-8"))
    relationships = json.loads((work / "pair_relationships.json").read_text(encoding="utf-8"))
    index = {row["image_id"]: row for row in index_rows}
    rel_cfg = config["relationship"]
    val_cfg = config["cluster_validation"]
    graph = nx.Graph()
    for row in index_rows:
        graph.add_node(row["image_id"])
    edge_rows = []
    for row in relationships:
        if row["relationship_type"] != "UNRELATED" and float(row["relationship_score"]) >= rel_cfg["edge_threshold"]:
            graph.add_edge(row["image_a"], row["image_b"], **row)
            edge_rows.append(row)

    clusters = []
    members = []
    group_no = 1
    for component in nx.connected_components(graph):
        if len(component) < 2:
            continue
        sub = graph.subgraph(component).copy()
        edges = list(sub.edges(data=True))
        scores = [float(data["relationship_score"]) for _, _, data in edges]
        avg_sim = sum(scores) / len(scores) if scores else 0.0
        min_sim = min(scores) if scores else 0.0
        strong_edges = sum(score >= rel_cfg["strong_edge_threshold"] for score in scores)
        strong_ratio = strong_edges / len(scores) if scores else 0.0
        if nx.is_connected(sub):
            lengths = dict(nx.all_pairs_shortest_path_length(sub))
            diameter = max(max(v.values()) for v in lengths.values()) if lengths else 0
            diameter_norm = diameter / max(1, len(component) - 1)
        else:
            diameter_norm = 1.0
        status, notes = status_for(avg_sim, min_sim, diameter_norm, strong_ratio, val_cfg)
        canonical = max(component, key=lambda image_id: quality_score(index[image_id]))
        group_id = f"DUP-{group_no:05d}"
        group_no += 1
        relation_counts = defaultdict(int)
        for _, _, data in edges:
            relation_counts[data["relationship_type"]] += 1
        dominant_relation = max(relation_counts, key=relation_counts.get) if relation_counts else "RELATED_ONLY"
        clusters.append({
            "duplicate_group_id": group_id,
            "canonical_image": canonical,
            "jumlah_gambar": len(component),
            "member_images": "; ".join(sorted(component)),
            "average_similarity": round(avg_sim, 6),
            "minimum_similarity": round(min_sim, 6),
            "cluster_confidence": "HIGH" if status == "VALID" else "MEDIUM" if status == "NEED_REVIEW" else "LOW",
            "cluster_status": status,
            "cluster_validation_notes": notes,
            "strong_edge_ratio": round(strong_ratio, 6),
            "cluster_diameter": round(diameter_norm, 6),
            "relationship_type_dominant": dominant_relation,
        })
        for image_id in sorted(component):
            row = index[image_id]
            members.append({
                "duplicate_group_id": group_id,
                "image_id": image_id,
                "nama_file": row["nama_file"],
                "path_rel": row["path_rel"],
                "ultg": row["ultg"],
                "kode_l1": row["kode_l1"],
                "is_canonical": "YA" if image_id == canonical else "TIDAK",
                "quality_score": quality_score(row),
            })

    for path, rows in [(work / "clusters.csv", clusters), (work / "cluster_members.csv", members)]:
        fields = list(rows[0]) if rows else ["duplicate_group_id"]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    (work / "clusters.json").write_text(json.dumps(clusters, ensure_ascii=False, indent=2), encoding="utf-8")
    (work / "cluster_members.json").write_text(json.dumps(members, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"clusters": len(clusters), "cluster_members": len(members), "edges": len(edge_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
