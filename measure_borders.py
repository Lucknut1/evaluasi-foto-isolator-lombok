from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from PIL import Image
import os
import pandas as pd
import numpy as np

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
WORK = ROOT / "outputs" / "lapis1_work"


def one(path_rel):
    path = ROOT / path_rel
    with Image.open(path) as src:
        im = src.convert("RGB")
        im.thumbnail((160, 213), Image.Resampling.LANCZOS)
    arr = np.asarray(im, dtype=np.int16)
    h, w = arr.shape[:2]
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    green = (g >= 90) & (g > r + 7) & (g > b + 2)
    green[: int(h * .24), : int(w * .72)] = False
    band = np.zeros_like(green)
    band[:3, :] = True
    band[-3:, :] = True
    band[:, :3] = True
    band[:, -3:] = True
    count = int((green & band).sum())
    sides = [int(green[:3, :].sum()), int(green[-3:, :].sum()), int(green[:, :3].sum()), int(green[:, -3:].sum())]
    return path_rel, count, max(sides)


def main():
    df = pd.read_csv(WORK / "hasil_lapis1.csv")
    candidates = df.loc[df.kode.eq("P"), "path_rel"].tolist()
    workers = min(8, max(1, (os.cpu_count() or 2)-1))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        vals = list(pool.map(one, candidates, chunksize=32))
    out = pd.DataFrame(vals, columns=["path_rel", "green_border_pixels", "green_border_side_max"])
    out.to_csv(WORK / "border_metrics.csv", index=False, encoding="utf-8-sig")
    print(out[["green_border_pixels", "green_border_side_max"]].quantile([0,.25,.5,.75,.9,.95,.99,1]))


if __name__ == "__main__":
    main()

