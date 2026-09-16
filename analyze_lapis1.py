from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from PIL import Image, ImageFilter, ImageStat, ImageFile
import csv
import math
import os

import numpy as np

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
OUT = ROOT / "outputs" / "lapis1_work"
FOLDERS = ["ULTG LOMBOK BARAT", "ULTG LOMBOK TIMUR", "ULTG SUMBAWA"]
ImageFile.LOAD_TRUNCATED_IMAGES = False


def largest_component(mask: np.ndarray) -> tuple[int, int, int, int, int, bool]:
    """Return area, width, height, max dimension, min dimension, touches border."""
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=np.uint8)
    best = (0, 0, 0, 0, 0, False)
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = 1
        area = 0
        minx = maxx = sx
        miny = maxy = sy
        touch = False
        while stack:
            y, x = stack.pop()
            area += 1
            minx = min(minx, x)
            maxx = max(maxx, x)
            miny = min(miny, y)
            maxy = max(maxy, y)
            touch = touch or x == 0 or y == 0 or x == w - 1 or y == h - 1
            for ny in range(max(0, y - 1), min(h, y + 2)):
                for nx in range(max(0, x - 1), min(w, x + 2)):
                    if not seen[ny, nx] and mask[ny, nx]:
                        seen[ny, nx] = 1
                        stack.append((ny, nx))
        bw = maxx - minx + 1
        bh = maxy - miny + 1
        cand = (area, bw, bh, max(bw, bh), min(bw, bh), touch)
        if cand[0] > best[0]:
            best = cand
    return best


def dilate(mask: np.ndarray, rounds: int = 2) -> np.ndarray:
    out = mask.copy()
    h, w = out.shape
    for _ in range(rounds):
        src = out.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                out[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] |= src[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    return out


def metrics(path_text: str) -> dict:
    path = Path(path_text)
    ultg = path.parts[-3]
    row = {
        "ultg": ultg,
        "nama_file": path.name,
        "path_rel": str(path.relative_to(ROOT)),
        "ukuran_byte": path.stat().st_size,
    }
    try:
        with Image.open(path) as src:
            src.load()
            row["format"] = src.format or ""
            row["lebar"] = src.width
            row["tinggi"] = src.height
            im = src.convert("RGB")
            im.thumbnail((160, 213), Image.Resampling.LANCZOS)
            arr = np.asarray(im, dtype=np.int16)
        gray = np.asarray(im.convert("L"), dtype=np.float32)
        h, w = gray.shape
        # Abaikan area overlay teks kiri atas saat mengukur objek utama.
        usable = np.ones((h, w), dtype=bool)
        usable[: int(h * 0.24), : int(w * 0.72)] = False
        vals = gray[usable]
        edge = np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        edge_vals = edge[2:-2, 2:-2]
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        mx = arr.max(axis=2)
        mn = arr.min(axis=2)
        sat = mx - mn
        green = (g >= 90) & (g > r + 7) & (g > b + 2) & usable
        pale_ins = (gray >= 150) & (sat <= 42) & (edge >= 18) & usable
        candidate = green | pale_ins
        # Hilangkan piksel tunggal dengan syarat sedikitnya dua tetangga kandidat.
        neigh = np.zeros_like(candidate, dtype=np.uint8)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neigh[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] += candidate[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
        candidate &= neigh >= 2
        comp_area, comp_w, comp_h, comp_long, comp_short, comp_touch = largest_component(candidate)
        green_area, green_w, green_h, green_long, green_short, green_touch = largest_component(dilate(green, 2))
        dark = (gray < 85) & usable
        blue_sky = (b > r + 20) & (b >= g) & (b > 100) & usable
        vegetation = (g > r + 12) & (g > b + 8) & (gray < 145) & usable
        row.update({
            "status_baca": "OK",
            "mean_luma": round(float(vals.mean()), 3),
            "std_luma": round(float(vals.std()), 3),
            "clip_gelap": round(float((vals <= 8).mean()), 6),
            "clip_terang": round(float((vals >= 247).mean()), 6),
            "edge_mean": round(float(edge_vals.mean()), 3),
            "edge_std": round(float(edge_vals.std()), 3),
            "dark_ratio": round(float(dark.mean()), 6),
            "sky_ratio": round(float(blue_sky.mean()), 6),
            "vegetasi_ratio": round(float(vegetation.mean()), 6),
            "candidate_ratio": round(float(candidate.mean()), 6),
            "chroma_std": round(float(np.std(r-g) + np.std(g-b)), 3),
            "comp_area": comp_area,
            "comp_w": comp_w,
            "comp_h": comp_h,
            "comp_long": comp_long,
            "comp_short": comp_short,
            "comp_touch": int(comp_touch),
            "green_area": green_area,
            "green_w": green_w,
            "green_h": green_h,
            "green_long": green_long,
            "green_short": green_short,
            "green_touch": int(green_touch),
            "thumb_w": w,
            "thumb_h": h,
        })
    except Exception as exc:
        row.update({
            "status_baca": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        })
    return row


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for folder in FOLDERS:
        paths.extend(str(p) for p in sorted((ROOT / folder).rglob("*.jpg")))
    workers = min(8, max(1, (os.cpu_count() or 2) - 1))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(metrics, paths, chunksize=32))
    fields = sorted({key for row in rows for key in row})
    out_path = OUT / "metrics_lapis1.csv"
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    ok = sum(r.get("status_baca") == "OK" for r in rows)
    print(f"Selesai: {len(rows)} foto, {ok} terbaca, {len(rows)-ok} error")
    print(out_path)


if __name__ == "__main__":
    main()
