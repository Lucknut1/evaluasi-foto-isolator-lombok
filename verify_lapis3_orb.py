"""Lapis 3 tahap 3: ORB, pHash, dHash, dan homography verification."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lapis3_config.json"


def load_gray(path: Path, max_dimension: int):
    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("gambar tidak dapat dibaca OpenCV")
    height, width = gray.shape[:2]
    longest = max(height, width)
    if max_dimension and longest > max_dimension:
        scale = max_dimension / longest
        gray = cv2.resize(gray, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
    return gray


def compute_pair(pair, index, orb, matcher, orb_cfg):
    a, b = index[pair["image_a"]], index[pair["image_b"]]
    path_a, path_b = ROOT / a["path_rel"], ROOT / b["path_rel"]
    result = dict(pair)
    result.update({
        "phash_distance": None,
        "dhash_distance": None,
        "keypoints_image_a": 0,
        "keypoints_image_b": 0,
        "total_matches": 0,
        "good_matches": 0,
        "geometrically_consistent_matches": 0,
        "feature_match_score": 0.0,
        "orb_status": "OK",
    })
    try:
        if a.get("phash") and b.get("phash"):
            result["phash_distance"] = int(imagehash.hex_to_hash(a["phash"]) - imagehash.hex_to_hash(b["phash"]))
        else:
            with Image.open(path_a) as im_a, Image.open(path_b) as im_b:
                result["phash_distance"] = int(imagehash.phash(im_a.convert("RGB")) - imagehash.phash(im_b.convert("RGB")))
        if a.get("dhash") and b.get("dhash"):
            result["dhash_distance"] = int(imagehash.hex_to_hash(a["dhash"]) - imagehash.hex_to_hash(b["dhash"]))
        else:
            with Image.open(path_a) as im_a, Image.open(path_b) as im_b:
                result["dhash_distance"] = int(imagehash.dhash(im_a.convert("RGB")) - imagehash.dhash(im_b.convert("RGB")))
        gray_a = load_gray(path_a, int(orb_cfg.get("max_dimension", 0)))
        gray_b = load_gray(path_b, int(orb_cfg.get("max_dimension", 0)))
        key_a, desc_a = orb.detectAndCompute(gray_a, None)
        key_b, desc_b = orb.detectAndCompute(gray_b, None)
        result["keypoints_image_a"] = len(key_a or [])
        result["keypoints_image_b"] = len(key_b or [])
        if desc_a is not None and desc_b is not None:
            knn = matcher.knnMatch(desc_a, desc_b, k=2)
            good = []
            for match in knn:
                if len(match) < 2:
                    continue
                m, n = match
                if m.distance < orb_cfg["ratio_test"] * n.distance:
                    good.append(m)
            result["total_matches"] = len(knn)
            result["good_matches"] = len(good)
            inliers = 0
            if len(good) >= orb_cfg["min_good_matches"]:
                src = np.float32([key_a[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst = np.float32([key_b[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                _matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, orb_cfg["ransac_reproj_threshold"])
                inliers = int(mask.sum()) if mask is not None else 0
            result["geometrically_consistent_matches"] = inliers
            denom = max(1, min(result["keypoints_image_a"], result["keypoints_image_b"]))
            result["feature_match_score"] = round(min(1.0, inliers / denom), 6)
    except Exception as exc:
        result["orb_status"] = f"ERROR: {type(exc).__name__}: {exc}"
    return result


def write_outputs(work: Path, output: list[dict]):
    fields = list(output[0]) if output else ["image_a", "image_b"]
    with (work / "verified_pairs.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    (work / "verified_pairs.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--no-resume", action="store_true", help="Abaikan checkpoint verified_pairs.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    work = ROOT / config["paths"]["work_dir"]
    index = {row["image_id"]: row for row in json.loads((work / "image_index.json").read_text(encoding="utf-8"))}
    candidates = json.loads((work / "candidate_pairs.json").read_text(encoding="utf-8"))
    output = []
    checkpoint_path = work / "verified_pairs.json"
    if checkpoint_path.exists() and not args.no_resume:
        try:
            output = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if len(output) > len(candidates) or any(
                (old.get("image_a"), old.get("image_b")) != (new.get("image_a"), new.get("image_b"))
                for old, new in zip(output, candidates)
            ):
                raise ValueError("checkpoint tidak cocok dengan candidate_pairs")
            print(json.dumps({"resuming_from": len(output), "total_pairs": len(candidates)}, ensure_ascii=False), flush=True)
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            raise SystemExit(f"Checkpoint ORB tidak dapat dipakai: {exc}. Jalankan dengan --no-resume bila memang ingin mengulang.") from exc
    orb_cfg = config["orb"]
    orb = cv2.ORB_create(
        nfeatures=orb_cfg["nfeatures"],
        scaleFactor=orb_cfg["scale_factor"],
        nlevels=orb_cfg["nlevels"],
    )
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    progress_interval = int(orb_cfg.get("progress_interval", 5000))
    start = len(output)
    for idx, pair in enumerate(candidates[start:], start=start + 1):
        output.append(compute_pair(pair, index, orb, matcher, orb_cfg))
        if progress_interval and idx % progress_interval == 0:
            write_outputs(work, output)
            print(json.dumps({"processed_pairs": idx, "total_pairs": len(candidates)}, ensure_ascii=False), flush=True)
    write_outputs(work, output)
    print(json.dumps({"candidate_pairs": len(candidates), "verified_pairs": len(output)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
