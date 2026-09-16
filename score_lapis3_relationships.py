"""Lapis 3 tahap 4: relationship score, type, confidence, dan evidence."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lapis3_config.json"


def finite(value):
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def optional_score(value, thresholds):
    if not finite(value):
        return None
    if value <= thresholds[0]:
        return 1.0
    if value <= thresholds[1]:
        return 0.6
    return 0.0


def classify(row, config):
    rel = config["relationship"]
    emb = float(row["embedding_similarity"])
    phash = row.get("phash_distance")
    feature = float(row.get("feature_match_score") or 0.0)
    gps = optional_score(row.get("gps_distance_meter"), (rel["gps_same_meter"], rel["gps_near_meter"]))
    time = optional_score(row.get("time_difference_second"), (rel["time_same_second"], rel["time_near_second"]))
    phash_score = None if not finite(phash) else max(0.0, 1.0 - float(phash) / 16.0)
    components = {"embedding": emb, "feature": feature, "phash": phash_score, "gps": gps, "time": time}
    weights = rel["weights"]
    available = [(name, value, weights[name]) for name, value in components.items() if value is not None]
    denominator = sum(weight for _, _, weight in available) or 1.0
    score = sum(value * weight for _, value, weight in available) / denominator
    evidence = []
    evidence.append("embedding_high" if emb >= 0.95 else "embedding_medium" if emb >= 0.80 else "embedding_low")
    evidence.append("feature_match_high" if feature >= 0.25 else "feature_match_low")
    if phash is None:
        evidence.append("phash_unknown")
    elif phash <= 4:
        evidence.append("phash_low_distance")
    elif phash <= 8:
        evidence.append("phash_near_distance")
    else:
        evidence.append("phash_far_distance")
    if gps is None:
        evidence.append("gps_unknown")
    elif gps >= 1:
        evidence.append("gps_same")
    elif gps > 0:
        evidence.append("gps_near")
    else:
        evidence.append("gps_far")
    if time is None:
        evidence.append("time_unknown")
    elif time >= 1:
        evidence.append("time_close")
    elif time > 0:
        evidence.append("time_near")
    else:
        evidence.append("time_far")

    if row.get("image_hash_a") and row.get("image_hash_a") == row.get("image_hash_b"):
        relation = "EXACT_DUPLICATE"
    elif emb >= rel["near_duplicate_embedding"] and phash is not None and phash <= rel["near_duplicate_phash_distance"]:
        relation = "NEAR_DUPLICATE"
    elif score >= rel["same_capture_score"] and (time == 1.0 or gps == 1.0):
        relation = "SAME_CAPTURE"
    elif score >= rel["same_object_score"] and feature >= 0.02:
        relation = "SAME_OBJECT"
    elif score >= rel["related_score"]:
        relation = "RELATED_ONLY"
    else:
        relation = "UNRELATED"
    confidence_cutoffs = rel["confidence"]
    confidence = "VERY_HIGH" if score >= confidence_cutoffs["very_high"] else "HIGH" if score >= confidence_cutoffs["high"] else "MEDIUM" if score >= confidence_cutoffs["medium"] else "LOW"
    row.update({
        "phash_score": None if phash_score is None else round(phash_score, 6),
        "gps_proximity_score": gps,
        "time_proximity_score": time,
        "relationship_score": round(score, 6),
        "relationship_type": relation,
        "duplicate_confidence": confidence,
        "duplicate_evidence": ";".join(evidence),
    })
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    work = ROOT / config["paths"]["work_dir"]
    rows = json.loads((work / "verified_pairs.json").read_text(encoding="utf-8"))
    index = {row["image_id"]: row for row in json.loads((work / "image_index.json").read_text(encoding="utf-8"))}
    for row in rows:
        row["image_hash_a"] = index[row["image_a"]]["image_hash"]
        row["image_hash_b"] = index[row["image_b"]]["image_hash"]
        classify(row, config)
    fields = list(rows[0]) if rows else ["image_a", "image_b"]
    with (work / "pair_relationships.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (work / "pair_relationships.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pairs": len(rows), "edges": sum(row["relationship_type"] != "UNRELATED" for row in rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
