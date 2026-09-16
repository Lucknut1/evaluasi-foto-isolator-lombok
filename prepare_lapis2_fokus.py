"""Perbarui Lapis 2 memakai master hanya sebagai guard-rail internal.

Master dipakai untuk cakupan dan pemilihan sampel audit, tidak disalin ke
keluaran Lapis 2. Keputusan dan kode Lapis 1 hanya dibaca sebagai konteks.
"""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import csv
import hashlib
import json
import math
import shutil

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "outputs/lapis2_work"
OUT = ROOT / "outputs/lapis2_20260913"
MASTER_PATH = ROOT / "Dataset_master.xlsx"
L1_DATA_PATH = ROOT / "outputs/lapis1_work/hasil_lapis1.csv"
L1_JSON_PATH = ROOT / "outputs/lapis1_work/hasil_lapis1.json"
L1_XLSX_PATH = ROOT / "outputs/lapis1_20260912_01a095d1/Hasil_Evaluasi_Lapis_1_Foto_Isolator.xlsx"
L1_HTML_PATH = ROOT / "outputs/lapis1_20260912_01a095d1/Dashboard_Evaluasi_Lapis_1_Foto_Isolator.html"
FEATURES = [
    "ragu2", "cakupan_foto", "jumlah_renteng_terbaca", "arah_isolator",
    "bahan_isolator", "cahaya", "ketajaman", "noise", "halangan",
    "isi_frame_terbanyak", "bagian_renteng_terlihat",
]
CODES = ["S", "J", "O", "B", "P", "K", "H", "D", "L"]
SAMPLE_SIZE = 1500


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_sample(rows, master_lookup):
    """Pilih sampel deterministik dari foto yang lolos guard-rail cakupan."""
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        master_row = master_lookup[(row["ultg"], row["nama_file"])]
        if master_row["in_scope"] is not True:
            continue
        groups[(row["ultg"], row["kode"], master_row["asset_norm"])].append(i)

    quotas = {
        key: min(len(ids), max(4, round(2 * math.sqrt(len(ids)))) )
        for key, ids in groups.items()
    }
    remaining = SAMPLE_SIZE - sum(quotas.values())
    if remaining < 0:
        raise ValueError("Alokasi minimum strata melebihi jumlah sampel")
    while remaining:
        choices = [key for key, ids in groups.items() if quotas[key] < len(ids)]
        if not choices:
            raise ValueError("Tidak ada strata tersisa untuk sampel")
        key = max(
            choices,
            key=lambda item: (len(groups[item]) - quotas[item]) / math.sqrt(len(groups[item])),
        )
        quotas[key] += 1
        remaining -= 1

    chosen = set()
    for key, ids in groups.items():
        ids.sort(key=lambda i: hashlib.sha256(rows[i]["path_rel"].encode("utf-8")).hexdigest())
        chosen.update(ids[:quotas[key]])
    if len(chosen) != SAMPLE_SIZE:
        raise ValueError(f"Sampel audit berjumlah {len(chosen)}, bukan {SAMPLE_SIZE}")
    return chosen, quotas


def main():
    backup = WORK / "sebelum_fokus_20260913"
    backup.mkdir(exist_ok=True)
    for path in [
        *OUT.glob("*.xlsx"),
        *OUT.glob("*.html"),
        WORK / "hasil_lapis2.json",
        WORK / "hasil_lapis2.csv",
        WORK / "summary_lapis2.json",
        WORK / "build_lapis2.mjs",
    ]:
        if path.exists() and not (backup / path.name).exists():
            shutil.copy2(path, backup / path.name)

    original = json.loads((backup / "hasil_lapis2.json").read_text(encoding="utf-8"))
    if len(original) != 26299:
        raise ValueError("Snapshot awal Lapis 2 berubah")

    # Jangan menimpa koreksi manual yang sudah tersimpan di workbook lama.
    workbook = openpyxl.load_workbook(
        backup / "Hasil_Evaluasi_Lapis_2_Foto_Isolator.xlsx",
        read_only=True,
        data_only=True,
    )
    source = {(row["ultg"], row["nama_file"]): row for row in original}
    edits = []
    for row in workbook["Ciri per Foto"].iter_rows(min_row=5, values_only=True):
        if not row[0]:
            continue
        current = source[(row[0], row[1])]
        if any(
            (row[7 + i] or "") != (current[feature] or "")
            for i, feature in enumerate(FEATURES)
        ) or (row[24] or "BELUM") != (current.get("validasi_manual_lapis2") or "BELUM") \
                or (row[25] or "") != (current.get("catatan_reviewer") or ""):
            edits.append(row[1])
    workbook.close()
    if edits:
        raise ValueError(f"Workbook contains {len(edits)} edits requiring preservation")

    # Guard-rail internal: hanya kunci, status cakupan, dan asset untuk strata.
    master = pd.read_excel(MASTER_PATH, sheet_name="master", keep_default_na=False)
    master["nama_file"] = (
        master["file_id"].astype(str)
        .str.replace("\\", "/", regex=False)
        .str.rsplit("/", n=1)
        .str[-1]
    )
    key = ["ultg", "nama_file"]
    if master.duplicated(key).any():
        raise ValueError("Kunci master ULTG + nama file tidak unik")
    master_lookup = {
        (row["ultg"], row["nama_file"]): row
        for row in master.to_dict("records")
    }
    if len(master_lookup) != 26659:
        raise ValueError("Jumlah baris master berubah")

    l1 = pd.read_csv(L1_DATA_PATH, keep_default_na=False)
    l1_lookup = {(row["ultg"], row["nama_file"]): row for row in l1.to_dict("records")}
    if len(l1_lookup) != len(l1):
        raise ValueError("Kunci hasil Lapis 1 tidak unik")

    selected, quotas = choose_sample(original, master_lookup)
    rows = []
    missing_master = []
    for index, original_row in enumerate(original):
        key_value = (original_row["ultg"], original_row["nama_file"])
        if key_value not in master_lookup:
            missing_master.append(key_value)
            continue
        if key_value not in l1_lookup:
            raise ValueError(f"Foto Lapis 2 tidak ada di hasil Lapis 1: {key_value}")
        if original_row["kode"] != l1_lookup[key_value]["kode"]:
            raise ValueError(f"Kode Lapis 1 berubah untuk {key_value}")

        # Master hanya menentukan kelayakan baris dan sampel, tidak pernah
        # ditambahkan sebagai kolom atau label ke hasil Lapis 2.
        master_row = master_lookup[key_value]
        if master_row["in_scope"] is not True:
            continue
        row = dict(original_row)
        row["sampel_audit_1500"] = "YA" if index in selected else "TIDAK"
        if any(row[feature] is None for feature in FEATURES):
            raise ValueError(f"Nilai ciri tidak eksplisit untuk {key_value}")
        rows.append(row)

    if missing_master:
        raise ValueError(f"{len(missing_master)} foto tidak cocok dengan master")
    if len(rows) != 24818 or sum(row["sampel_audit_1500"] == "YA" for row in rows) != SAMPLE_SIZE:
        raise ValueError("Jumlah foto masuk cakupan atau sampel berubah")

    stats = {
        "total": len(rows),
        "sample": SAMPLE_SIZE,
        "by_ultg": dict(Counter(row["ultg"] for row in rows)),
        "features": {feature: dict(Counter(row[feature] for row in rows)) for feature in FEATURES},
        "unassessed_cells": sum(row["jumlah_belum_dinilai"] for row in rows),
        "rows_with_gaps": sum(row["jumlah_belum_dinilai"] > 0 for row in rows),
        "codes": dict(Counter(row["kode"] for row in rows)),
        "sample_by_ultg": dict(
            Counter(row["ultg"] for row in rows if row["sampel_audit_1500"] == "YA")
        ),
    }
    stats["relations"] = {
        feature: {
            value: {code: sum(row[feature] == value and row["kode"] == code for row in rows) for code in CODES}
            for value in stats["features"][feature]
        }
        for feature in FEATURES
    }
    for feature in FEATURES:
        if sum(sum(counts.values()) for counts in stats["relations"][feature].values()) != len(rows):
            raise ValueError(f"Relasi ciri dan kode tidak lengkap: {feature}")

    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "hasil_lapis2.json").write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    with (WORK / "hasil_lapis2.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (WORK / "summary_lapis2.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    guardrail = {
        "generated_at": datetime.now().isoformat(),
        "purpose": "internal_guardrail_only",
        "master_path": str(MASTER_PATH),
        "master_sha256": sha(MASTER_PATH),
        "master_rows": len(master),
        "master_key": "ULTG + nama_file",
        "eligible": len(rows),
        "sample": SAMPLE_SIZE,
        "excluded": len(original) - len(rows),
        "sample_strata": {" | ".join(key): value for key, value in quotas.items()},
        "l1_sha256": {
            str(path): sha(path)
            for path in [L1_DATA_PATH, L1_JSON_PATH, L1_XLSX_PATH, L1_HTML_PATH]
        },
        "l1_rows_checked": len(l1),
        "l1_codes_checked": len(rows),
        "public_output_columns": list(rows[0]),
        "master_columns_excluded": [
            "file_id", "asset_norm", "bulan", "in_scope_master", "kelompok_master",
            "status_master", "ocr_conf", "cocok_skor",
        ],
    }
    (WORK / "guardrail_internal.json").write_text(
        json.dumps(guardrail, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({key: stats[key] for key in ["total", "sample", "unassessed_cells", "rows_with_gaps", "codes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
