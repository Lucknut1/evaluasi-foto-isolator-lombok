from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat
import hashlib

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
OUT = ROOT / "outputs" / "lapis1_work"
OUT.mkdir(parents=True, exist_ok=True)

folders = ["ULTG LOMBOK BARAT", "ULTG LOMBOK TIMUR", "ULTG SUMBAWA"]
font = ImageFont.load_default()

for folder in folders:
    files = sorted((ROOT / folder).rglob("*.jpg"))
    ranked = sorted(files, key=lambda p: hashlib.sha256(str(p).encode("utf-8")).digest())
    sample = ranked[:25]
    thumb_w, thumb_h = 300, 400
    label_h = 42
    canvas = Image.new("RGB", (thumb_w * 5, (thumb_h + label_h) * 5), "white")
    draw = ImageDraw.Draw(canvas)
    for idx, path in enumerate(sample):
        x = (idx % 5) * thumb_w
        y = (idx // 5) * (thumb_h + label_h)
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((thumb_w, thumb_h))
                px = x + (thumb_w - im.width) // 2
                py = y + (thumb_h - im.height) // 2
                canvas.paste(im, (px, py))
                label = f"{idx+1:02d} {path.name[:32]}\n{im.width}x{im.height}"
        except Exception as exc:
            label = f"{idx+1:02d} ERROR {type(exc).__name__}"
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill="#F3F4F6")
        draw.text((x + 4, y + thumb_h + 4), label, fill="#111827", font=font)
    canvas.save(OUT / f"sample_{folder.lower().replace(' ', '_')}.jpg", quality=90)

