from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
WORK = ROOT / "outputs" / "lapis1_work"
OUT = WORK / "decision_review"
OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(WORK / "hasil_lapis1.csv")
border_path = WORK / "border_metrics.csv"
if border_path.exists():
    df = df.merge(pd.read_csv(border_path), on="path_rel", how="left")
else:
    df["green_border_side_max"] = 0
font = ImageFont.load_default()

sets = {code: part.sample(min(25, len(part)), random_state=100+i) for i, (code, part) in enumerate(df.groupby("kode"))}
sets["low_confidence"] = df[df.confidence == "rendah"].sample(25, random_state=199)
sets["P_border_high"] = df[df.kode.eq("P")].nlargest(25, "green_border_side_max")

for name, rows in sets.items():
    tw, th, lh = 300, 400, 58
    canvas = Image.new("RGB", (tw*5, (th+lh)*5), "white")
    draw = ImageDraw.Draw(canvas)
    for idx, row in enumerate(rows.itertuples(index=False)):
        path = ROOT / row.path_rel
        x, y = (idx % 5)*tw, (idx // 5)*(th+lh)
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((tw, th), Image.Resampling.LANCZOS)
            canvas.paste(im, (x+(tw-im.width)//2, y+(th-im.height)//2))
        label = (f"{idx+1:02d} {row.kode} {row.confidence} {row.nama_file[:18]}\n"
                 f"edge={row.edge_mean:.1f} dark={row.dark_ratio:.3f} bright={row.clip_terang:.3f}\n"
                 f"green={int(row.green_long)}/{int(row.green_short)} comp={int(row.comp_long)}/{int(row.comp_short)}")
        draw.rectangle((x, y+th, x+tw, y+th+lh), fill="#F3F4F6")
        draw.text((x+3, y+th+3), label, fill="#111827", font=font)
    canvas.save(OUT / f"{name}.jpg", quality=90)
    print(name, len(rows))
