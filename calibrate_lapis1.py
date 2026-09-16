from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
OUT = ROOT / "outputs" / "lapis1_work" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / "outputs" / "lapis1_work" / "metrics_lapis1.csv")
font = ImageFont.load_default()

sets = {
    "edge_low": df.nsmallest(25, "edge_mean"),
    "edge_low_close": df[df.dark_ratio >= df.dark_ratio.quantile(.65)].nsmallest(25, "edge_mean"),
    "bright_high": df.nlargest(25, "clip_terang"),
    "dark_high": df.nlargest(25, "clip_gelap"),
    "candidate_low": df.nsmallest(25, "comp_long"),
    "candidate_small": df[(df.comp_long > 0) & (df.comp_long <= df.comp_long.quantile(.15))].sample(25, random_state=11),
    "candidate_mid": df[(df.comp_long >= df.comp_long.quantile(.45)) & (df.comp_long <= df.comp_long.quantile(.55))].sample(25, random_state=12),
    "candidate_large": df.nlargest(25, "comp_long"),
    "touch_large": df[(df.comp_touch == 1) & (df.comp_long >= df.comp_long.quantile(.65))].sample(25, random_state=13),
    "vegetation_high": df.nlargest(25, "vegetasi_ratio"),
    "no_candidate_dark": df[(df.comp_long <= 8) & (df.dark_ratio >= .08)].nlargest(25, "dark_ratio"),
    "chroma_high": df.nlargest(25, "chroma_std"),
    "green_small": df[(df.green_long > 0) & (df.green_long <= df.green_long.quantile(.20))].sample(25, random_state=14),
    "green_mid": df[(df.green_long >= df.green_long.quantile(.45)) & (df.green_long <= df.green_long.quantile(.55))].sample(25, random_state=15),
    "green_large": df.nlargest(25, "green_long"),
}

for name, rows in sets.items():
    thumb_w, thumb_h, label_h = 300, 400, 58
    canvas = Image.new("RGB", (thumb_w * 5, (thumb_h + label_h) * 5), "white")
    draw = ImageDraw.Draw(canvas)
    for idx, row in enumerate(rows.itertuples(index=False)):
        path = ROOT / row.path_rel
        x = (idx % 5) * thumb_w
        y = (idx // 5) * (thumb_h + label_h)
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas.paste(im, (x + (thumb_w-im.width)//2, y + (thumb_h-im.height)//2))
            label = (f"{idx+1:02d} {row.nama_file[:23]}\n"
                     f"edge={row.edge_mean:.1f} dark={row.dark_ratio:.3f} bright={row.clip_terang:.3f}\n"
                     f"comp={int(row.comp_long)}/{int(row.comp_short)} green={int(row.green_long)}/{int(row.green_short)} chr={row.chroma_std:.1f}")
        except Exception as exc:
            label = f"ERROR {exc}"
        draw.rectangle((x, y+thumb_h, x+thumb_w, y+thumb_h+label_h), fill="#F3F4F6")
        draw.text((x+3, y+thumb_h+3), label, fill="#111827", font=font)
    canvas.save(OUT / f"{name}.jpg", quality=90)
    print(name, len(rows))
