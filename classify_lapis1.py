from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
WORK = ROOT / "outputs" / "lapis1_work"

NAMES = {
    "S": ("SESUAI", None),
    "D": ("BERKAS_RUSAK", 0),
    "O": ("SALAH_OBJEK", 1),
    "B": ("BLUR", 2),
    "K": ("SILAU", 3),
    "H": ("TERHALANG", 4),
    "J": ("TERLALU_JAUH", 5),
    "P": ("OBJEK_UTAMA_TERPOTONG", 6),
    "L": ("LAINNYA", 7),
}


def decide(r):
    # Urutan mengikuti prioritas keputusan dalam rencana implementasi.
    damaged = (
        r.status_baca != "OK"
        or (
            r.edge_mean > 55
            and r.sky_ratio < 0.12
            and r.chroma_std > 25
            and (r.edge_mean > 70 or r.dark_ratio > 0.45)
        )
    )
    if damaged:
        return "D", "tinggi", "Pola noise warna atau kerusakan data menutup detail foto."

    wrong_object = (
        (r.green_long <= 4 and r.comp_long <= 8 and r.dark_ratio > 0.035)
        or (r.green_long <= 2 and r.comp_long <= 4 and r.dark_ratio > 0.018)
    )
    if wrong_object:
        return "O", "rendah", "Tidak ditemukan bentuk renteng yang terbaca pada area objek."

    blurred = (
        (r.edge_mean < 18.5 and r.green_long >= 20 and r.dark_ratio >= 0.015)
        or (r.edge_mean < 17 and r.comp_long >= 20 and r.dark_ratio >= 0.03)
    )
    if blurred:
        confidence = "tinggi" if r.edge_mean < 16 else "sedang"
        return "B", confidence, "Ketajaman tepi objek rendah sehingga detail piringan tidak stabil."

    glare = (
        r.clip_terang >= 0.12
        or r.mean_luma >= 205
        or (r.mean_luma < 88 and r.dark_ratio > 0.35)
    )
    if glare:
        confidence = "tinggi" if r.clip_terang >= 0.22 or r.mean_luma >= 220 else "sedang"
        return "K", confidence, "Paparan ekstrem atau area terang terpotong menghilangkan detail piringan."

    obstructed = (
        r.vegetasi_ratio >= 0.14
        and r.dark_ratio >= 0.18
        and r.sky_ratio >= 0.10
    )
    if obstructed:
        confidence = "tinggi" if r.vegetasi_ratio >= 0.22 else "sedang"
        return "H", confidence, "Vegetasi atau objek depan menutup bagian penting area penilaian."

    too_far = (
        (r.green_long < 18 and r.comp_long < 28)
        or (r.green_long < 12 and r.dark_ratio < 0.06)
    )
    if too_far:
        confidence = "tinggi" if r.green_long < 9 and r.comp_long < 16 else "sedang"
        return "J", confidence, "Renteng terlalu kecil untuk memastikan detail piringan satu per satu."

    cropped = (
        r.green_touch == 1
        and r.green_long >= 25
        and r.green_short <= 20
        and r.green_area <= 1200
    )
    if cropped:
        return "P", "sedang", "Kandidat renteng utama menyentuh tepi frame dan berpotensi terpotong."

    if r.green_long >= 35 and r.edge_mean >= 24 and r.clip_terang < 0.05:
        confidence = "tinggi"
    elif r.green_long >= 22 and r.edge_mean >= 21:
        confidence = "sedang"
    else:
        confidence = "rendah"
    return "S", confidence, "Renteng terlihat dan ukuran serta ketajamannya cukup untuk penilaian foto."


def main():
    df = pd.read_csv(WORK / "metrics_lapis1.csv")
    # Alias untuk menjaga nama atribut tetap singkat pada fungsi keputusan.
    df["vegetasi_ratio"] = pd.to_numeric(df["vegetasi_ratio"], errors="coerce").fillna(0)
    decisions = []
    for row in df.itertuples(index=False):
        decisions.append(decide(row))
    df["kode"] = [x[0] for x in decisions]
    df["nama_keputusan"] = df["kode"].map(lambda x: NAMES[x][0])
    df["prioritas"] = df["kode"].map(lambda x: NAMES[x][1])
    df["confidence"] = [x[1] for x in decisions]
    df["alasan"] = [x[2] for x in decisions]
    df["perlu_review_manual"] = df["confidence"].eq("rendah").map({True: "YA", False: "TIDAK"})
    ordered = [
        "ultg", "nama_file", "path_rel", "kode", "nama_keputusan", "prioritas",
        "confidence", "perlu_review_manual", "alasan", "lebar", "tinggi", "ukuran_byte",
        "mean_luma", "clip_gelap", "clip_terang", "edge_mean", "dark_ratio", "sky_ratio",
        "vegetasi_ratio", "green_long", "green_short", "green_touch", "comp_long", "comp_short",
        "chroma_std", "status_baca",
    ]
    df[ordered].to_csv(WORK / "hasil_lapis1.csv", index=False, encoding="utf-8-sig")
    records = df[ordered].astype(object).where(pd.notnull(df[ordered]), None).to_dict(orient="records")
    (WORK / "hasil_lapis1.json").write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    summary = {
        "total": int(len(df)),
        "by_code": {str(k): int(v) for k, v in df.kode.value_counts().sort_index().items()},
        "by_ultg_code": {
            str(ultg): {str(k): int(v) for k, v in part.kode.value_counts().sort_index().items()}
            for ultg, part in df.groupby("ultg")
        },
        "confidence": {str(k): int(v) for k, v in df.confidence.value_counts().items()},
        "review_manual": int(df.perlu_review_manual.eq("YA").sum()),
    }
    (WORK / "summary_lapis1.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
