"""Join tepat Lapis 2 dengan master. Tidak mengubah keputusan Lapis 1.

Sampel audit baru hanya berasal dari foto yang menurut master masuk cakupan.
Label visual tetap hipotesis Lapis 2 awal dan bukan kebenaran dari master.
"""

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import hashlib
import json
import math

import pandas as pd

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
OUT = ROOT / "outputs" / "lapis2_master_work"
FEATURES = [
    "ragu2", "cakupan_foto", "jumlah_renteng_terbaca", "arah_isolator",
    "bahan_isolator", "cahaya", "ketajaman", "noise", "halangan",
    "isi_frame_terbanyak", "bagian_renteng_terlihat",
]
SAMPLE_SIZE = 1500


def clean_cell(x):
    if pd.isna(x):
        return None
    if isinstance(x, (datetime, pd.Timestamp)):
        return x.isoformat(timespec="seconds")
    if hasattr(x, "item"):
        return x.item()
    return x


def choose_sample(data):
    eligible = data.index[data.in_scope_master.eq(True)].tolist()
    groups = defaultdict(list)
    for i in eligible:
        r = data.loc[i]
        # Master asset membedakan form piringan umum dari kondisi fisik.
        groups[(r.ultg, r.kode, r.asset_norm)].append(i)
    if len(eligible) < SAMPLE_SIZE:
        raise ValueError("Foto masuk cakupan lebih sedikit dari jumlah sampel")
    quotas = {k: min(len(v), max(4, round(2 * math.sqrt(len(v))))) for k, v in groups.items()}
    remaining = SAMPLE_SIZE - sum(quotas.values())
    if remaining < 0:
        raise ValueError("Alokasi minimum strata melebihi jumlah sampel")
    while remaining:
        choices = [k for k, v in groups.items() if quotas[k] < len(v)]
        if not choices:
            raise ValueError("Tidak ada strata tersisa untuk sampel")
        # Kelas besar masih mendapat tambahan. Pembagi akar mencegah S mendominasi.
        key = max(choices, key=lambda k: (len(groups[k]) - quotas[k]) / math.sqrt(len(groups[k])))
        quotas[key] += 1
        remaining -= 1
    chosen = set()
    for key, ids in groups.items():
        ids.sort(key=lambda i: hashlib.sha256(data.at[i, "path_rel"].encode("utf-8")).hexdigest())
        chosen.update(ids[:quotas[key]])
    assert len(chosen) == SAMPLE_SIZE
    return chosen, quotas


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_master = ROOT / "Dataset_master.xlsx"
    master = pd.read_excel(source_master, sheet_name="master", engine="openpyxl")
    old = pd.read_csv(ROOT / "outputs/lapis2_work/hasil_lapis2.csv", encoding="utf-8-sig")
    master["nama_file"] = master.file_id.astype(str).str.replace("\\", "/", regex=False).str.rsplit("/", n=1).str[-1]
    key = ["ultg", "nama_file"]
    if master.duplicated(key).any() or old.duplicated(key).any():
        raise ValueError("Kunci ULTG + nama file tidak unik")
    cols = key + ["file_id", "asset_norm", "bulan", "in_scope", "kelompok", "ocr_conf", "cocok_skor"]
    joined = old.merge(master[cols], on=key, how="left", validate="one_to_one", indicator=True)
    if len(joined) != 26299 or not joined._merge.eq("both").all():
        raise ValueError("Foto Lapis 2 tidak seluruhnya cocok dengan master")
    missing = master.merge(old[key], on=key, how="left", indicator=True)
    missing = missing.loc[missing._merge.eq("left_only"), key + ["file_id", "asset_norm", "bulan", "in_scope", "kelompok"]]
    missing = missing.rename(columns={"in_scope": "in_scope_master", "kelompok": "kelompok_master"})
    if len(missing) != 360:
        raise ValueError("Rekonsiliasi master tanpa foto berubah")

    joined = joined.drop(columns=["_merge", "sampel_audit_1500"])
    joined = joined.rename(columns={"in_scope": "in_scope_master", "kelompok": "kelompok_master"})
    joined["status_cakupan"] = joined.in_scope_master.map({True: "MASUK_CAKUPAN", False: "DI_LUAR_CAKUPAN"})
    joined["status_master"] = joined.kelompok_master.map({
        "POPULASI": "TERKONFIRMASI", "PERLU_CEK_JABATAN": "PERLU_CEK_JABATAN",
        "PERLU_CEK_OCR": "PERLU_CEK_OCR", "OUT_OF_SCOPE": "DI_LUAR_CAKUPAN"
    }).fillna("PERLU_CEK")
    chosen, quotas = choose_sample(joined)
    joined.insert(5, "sampel_audit_master", ["YA" if i in chosen else "TIDAK" for i in range(len(joined))])
    joined["asal_ciri_lapis2"] = "hipotesis_proksi_metrik_lapis1"
    # Master adalah metadata form, bukan label isi frame. Nilai ciri lama
    # dipertahankan, tetapi 1.481 foto luar cakupan tidak masuk denominator utama.
    ordered = ["ultg", "nama_file", "path_rel", "file_id", "asset_norm", "bulan",
               "in_scope_master", "status_cakupan", "kelompok_master", "status_master",
               "kode", "confidence", "sampel_audit_master", "review_manual_lapis1"] + FEATURES + [
               "status_lapis2", "asal_ciri_lapis2", "jumlah_belum_dinilai",
               "ciri_belum_dinilai", "ciri_semantik_perlu_verifikasi", "validasi_manual_lapis2",
               "catatan_reviewer", "ocr_conf", "cocok_skor"]
    data = joined[ordered].copy()
    data.to_csv(OUT / "hasil_lapis2_master.csv", index=False, encoding="utf-8-sig")
    records = [{k: clean_cell(v) for k, v in record.items()} for record in data.to_dict("records")]
    (OUT / "hasil_lapis2_master.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    missing.to_csv(OUT / "master_tanpa_foto.csv", index=False, encoding="utf-8-sig")
    missing_records = [{k: clean_cell(v) for k, v in record.items()} for record in missing.to_dict("records")]
    (OUT / "master_tanpa_foto.json").write_text(json.dumps(missing_records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    eligible = data.loc[data.in_scope_master.eq(True)]
    excluded = data.loc[data.in_scope_master.eq(False)]
    sample = data.loc[data.sampel_audit_master.eq("YA")]
    summary = {
        "master_total": len(master), "foto_total": len(data), "matched": len(data),
        "master_without_photo": len(missing), "master_without_photo_in_scope": int(missing.in_scope_master.sum()),
        "in_scope_photo": len(eligible), "out_of_scope_photo": len(excluded),
        "confirmed_population": int(data.kelompok_master.eq("POPULASI").sum()),
        "in_scope_pending_identity_or_ocr": int(eligible.kelompok_master.ne("POPULASI").sum()),
        "sample": len(sample), "sample_out_of_scope": int(sample.in_scope_master.eq(False).sum()),
        "eligible_with_gaps": int(eligible.jumlah_belum_dinilai.gt(0).sum()),
        "eligible_gap_cells": int(eligible.jumlah_belum_dinilai.sum()),
        "all_with_gaps": int(data.jumlah_belum_dinilai.gt(0).sum()),
        "all_gap_cells": int(data.jumlah_belum_dinilai.sum()),
        "sample_by_ultg": sample.ultg.value_counts().to_dict(),
        "sample_by_code": sample.kode.value_counts().to_dict(),
        "eligible_by_ultg": eligible.ultg.value_counts().to_dict(),
        "out_of_scope_by_asset": excluded.asset_norm.value_counts().to_dict(),
        "eligible_features": {f: eligible[f].value_counts(dropna=False).to_dict() for f in FEATURES},
        "all_features": {f: data[f].value_counts(dropna=False).to_dict() for f in FEATURES},
        "sample_strata": {" | ".join(k): int(v) for k, v in quotas.items()},
        "master_without_photo_by_group": missing.kelompok_master.value_counts().to_dict(),
    }
    (OUT / "summary_lapis2_master.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("eligible_features", "all_features", "sample_strata")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
