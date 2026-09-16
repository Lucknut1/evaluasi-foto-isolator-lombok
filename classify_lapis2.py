"""Lapis 2: ciri otomatis sebagai hipotesis, bukan label inspeksi final.

Menjaga keputusan Lapis 1 tetap apa adanya. Semua foto mendapat 11 ciri.
Kolom status dan metode membedakan pengukuran proksi dari penilaian manusia.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import json
import math

import pandas as pd

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
WORK = ROOT / "outputs" / "lapis1_work"
OUT = ROOT / "outputs" / "lapis2_work"

FEATURES = [
    "ragu2", "cakupan_foto", "jumlah_renteng_terbaca", "arah_isolator",
    "bahan_isolator", "cahaya", "ketajaman", "noise", "halangan",
    "isi_frame_terbanyak", "bagian_renteng_terlihat",
]


def num(row, name, default=0.0):
    val = row.get(name)
    if pd.isna(val):
        return default
    return float(val)


def classify(r):
    kode = r["kode"]
    gl = num(r, "green_long")
    cl = num(r, "comp_long")
    gs = num(r, "green_short")
    sky = num(r, "sky_ratio")
    dark = num(r, "dark_ratio")
    veg = num(r, "vegetasi_ratio")
    lum = num(r, "mean_luma", 127)
    edge = num(r, "edge_mean")
    clip = num(r, "clip_terang")
    chroma = num(r, "chroma_std")
    green_area = num(r, "green_area")
    cand_area = num(r, "candidate_ratio")
    touch = int(num(r, "green_touch"))
    gw, gh = num(r, "green_w"), num(r, "green_h")
    cw, ch = num(r, "comp_w"), num(r, "comp_h")
    h = num(r, "thumb_h", 213)

    # Ukuran kandidat merupakan proksi framing, bukan deteksi renteng yang tervalidasi.
    size = max(gl, cl) / max(h, 1)
    if size >= .40 and sky < .55:
        cakupan = "closeup_1_renteng" if green_area < 1100 else "closeup_beberapa_renteng"
    elif size >= .27:
        cakupan = "closeup_beberapa_renteng"
    elif size >= .17:
        cakupan = "setengah_tower"
    elif size >= .09:
        cakupan = "tower_penuh"
    else:
        cakupan = "tower_dan_lanskap" if sky >= .52 else "tower_penuh"

    # Tidak menghitung komponen hijau sebagai renteng. Gambar tanpa piringan
    # terbaca dan kelas J/B/O/D/K/H/P memerlukan penilai untuk jumlah pastinya.
    count = "0" if kode in ("O", "D") else "belum_dinilai"
    if kode == "S":
        count = "1" if cakupan == "closeup_1_renteng" else "belum_dinilai"

    # Bentuk geometri kandidat rentan tercampur tower/kabel. NA hanya saat
    # tidak ada kandidat; selebihnya estimasi dan selalu ditandai review.
    bw, bh = (gw, gh) if gl >= cl and gw * gh else (cw, ch)
    if kode in ("D", "O") or min(bw, bh) < 3:
        arah = "NA"
    elif bh >= 2.0 * bw:
        arah = "vertikal"
    elif bw >= 2.0 * bh:
        arah = "horizontal"
    else:
        arah = "miring"

    # Warna hijau dalam foto tidak membuktikan bahan kaca karena struktur
    # tower dan daun juga hijau. Nilai aman ialah tidak_jelas.
    bahan = "tidak_jelas"

    if lum < 85:
        cahaya = "terlalu_gelap"
    elif clip >= .11 or lum >= 205:
        cahaya = "terlalu_terang"
    elif clip >= .025 and sky >= .22:
        cahaya = "flare"
    elif sky >= .38 and dark >= .19 and lum < 145:
        cahaya = "backlit"
    elif lum < 135 and edge < 22 and sky >= .20:
        cahaya = "berkabut"
    else:
        cahaya = "normal"

    ketajaman = "blur" if kode == "B" or edge < 17 else "sedikit_blur" if edge < 25 else "tajam"
    # Chroma merupakan proksi yang lemah untuk noise, bukan ukuran ISO.
    noise = "banyak_noise" if chroma > 35 and dark > .30 else "sedikit_noise" if chroma > 25 and dark > .18 else "bersih"
    halangan = "pohon" if kode == "H" and veg >= .14 else "tidak_ada"
    if kode == "H" and veg < .14:
        halangan = "belum_dinilai"

    if sky >= .67 and dark < .18:
        frame = "langit_lanskap"
    elif dark >= .38 and sky < .35:
        frame = "rangka_tower"
    elif cand_area >= .16 and sky < .25:
        frame = "piringan_isolator"
    elif sky >= .38 and dark >= .18:
        frame = "seimbang"
    else:
        frame = "belum_dinilai"

    if kode in ("D", "O"):
        bagian = "NA"
    elif kode == "P" and touch:
        bagian = "belum_dinilai"  # Sisi yang terpotong tidak tersimpan di metrik L1.
    elif touch and size >= .12:
        bagian = "belum_dinilai"
    elif kode == "S" and size >= .20:
        bagian = "utuh"
    else:
        bagian = "belum_dinilai"

    ragu = "ya" if (r["confidence"] == "rendah" and kode in ("S", "J")) else "tidak"
    result = dict(zip(FEATURES, [ragu, cakupan, count, arah, bahan, cahaya,
                                  ketajaman, noise, halangan, frame, bagian]))
    uncertain = [x for x in FEATURES if result[x] == "belum_dinilai"]
    # Warna, arah, count, bagian, dan isi frame adalah identifikasi semantik
    # yang tidak tervalidasi pada pixel aggregate.
    high_risk = [x for x in ("jumlah_renteng_terbaca", "arah_isolator",
                            "bahan_isolator", "halangan", "isi_frame_terbanyak",
                            "bagian_renteng_terlihat") if x not in uncertain]
    result.update({
        "status_lapis2": "PERLU_VALIDASI",
        "metode": "proksi_metrik_lapis1",
        "jumlah_belum_dinilai": len(uncertain),
        "ciri_belum_dinilai": ", ".join(uncertain),
        "ciri_semantik_perlu_verifikasi": ", ".join(high_risk),
    })
    return result


def sample_ids(frame, target=1500):
    """Alokasi proporsional per ULTG/kode dengan oversampling kelas kecil."""
    groups = defaultdict(list)
    for i, r in frame.iterrows():
        groups[(r["ultg"], r["kode"])].append(i)
    # Semua strata ditampilkan, kelas langka diambil lebih banyak.
    budget = {}
    for key, ids in groups.items():
        budget[key] = min(len(ids), max(8, round(math.sqrt(len(ids)) * 2)))
    remaining = target - sum(budget.values())
    while remaining > 0:
        candidates = [k for k in groups if budget[k] < len(groups[k])]
        if not candidates:
            break
        ranked = sorted(candidates, key=lambda k: (len(groups[k]) - budget[k]) / math.sqrt(len(groups[k])), reverse=True)
        for key in ranked:
            if remaining <= 0:
                break
            budget[key] += 1
            remaining -= 1
    selected = set()
    for key, ids in groups.items():
        ids.sort(key=lambda i: hashlib.sha256(frame.at[i, "path_rel"].encode("utf-8")).hexdigest())
        selected.update(ids[:budget[key]])
    return selected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(WORK / "hasil_lapis1.csv", dtype={"path_rel": str})
    metrics = pd.read_csv(WORK / "metrics_lapis1.csv", dtype={"path_rel": str})
    extra = ["path_rel", "thumb_h", "green_area", "green_w", "green_h", "comp_w", "comp_h", "candidate_ratio", "std_luma"]
    data = base.merge(metrics[extra], on="path_rel", how="left", validate="one_to_one")
    assert len(data) == 26299 and data.path_rel.is_unique
    derived = pd.DataFrame([classify(r) for r in data.to_dict("records")])
    selected = sample_ids(data)
    output = pd.concat([data[["ultg", "nama_file", "path_rel", "kode", "confidence"]], derived], axis=1)
    output.insert(5, "sampel_audit_1500", ["YA" if i in selected else "TIDAK" for i in range(len(output))])
    output.insert(6, "review_manual_lapis1", data.perlu_review_manual.values)
    output["validasi_manual_lapis2"] = "BELUM"
    output["catatan_reviewer"] = ""
    output.to_csv(OUT / "hasil_lapis2.csv", index=False, encoding="utf-8-sig")
    records = output.astype(object).where(pd.notnull(output), None).to_dict("records")
    (OUT / "hasil_lapis2.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    summary = {
        "total": len(output), "sample": len(selected),
        "by_ultg": {str(k): int(v) for k, v in output.ultg.value_counts().items()},
        "sample_by_ultg_code": {f"{u} | {k}": int(len(g)) for (u, k), g in output[output.sampel_audit_1500.eq("YA")].groupby(["ultg", "kode"])},
        "features": {f: {str(k): int(v) for k, v in output[f].value_counts().items()} for f in FEATURES},
        "unassessed_cells": int(output.jumlah_belum_dinilai.sum()),
        "rows_with_gaps": int(output.jumlah_belum_dinilai.gt(0).sum()),
    }
    (OUT / "summary_lapis2.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": summary["total"], "sample": summary["sample"], "unassessed_cells": summary["unassessed_cells"], "rows_with_gaps": summary["rows_with_gaps"], "features": summary["features"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
