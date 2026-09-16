from collections import Counter, defaultdict
from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result")
master = pd.read_excel(ROOT / "Dataset_master.xlsx", sheet_name="master", engine="openpyxl")
l2 = pd.read_csv(ROOT / "outputs/lapis2_work/hasil_lapis2.csv", encoding="utf-8-sig")
master["nama_file"] = master.file_id.astype(str).str.replace("\\", "/", regex=False).str.rsplit("/", n=1).str[-1]
key = ["ultg", "nama_file"]

print("MASTER", len(master), "L2", len(l2))
print("MASTER_COLUMNS", list(master.columns))
print("DUP_KEYS_MASTER", int(master.duplicated(key).sum()), "DUP_KEYS_L2", int(l2.duplicated(key).sum()))
print("MASTER_GROUP", master.kelompok.value_counts(dropna=False).to_dict())
print("MASTER_SCOPE", master.in_scope.value_counts(dropna=False).to_dict())
print("MASTER_ASSET", master.asset_norm.value_counts(dropna=False).head(20).to_dict())
print("MASTER_DUPLICATES", master.is_duplikat.value_counts(dropna=False).to_dict())
print("OCR_CORE", master.ocr_inti.value_counts(dropna=False).to_dict())
print("OCR_CONF", master.ocr_conf.describe().to_dict())
print("MATCH_SCORE", master.cocok_skor.describe().to_dict())

merged = l2.merge(master, on=key, how="left", validate="one_to_one", indicator=True, suffixes=("_l2", "_master"))
print("MATCH", merged._merge.value_counts().to_dict())
print("UNMATCHED_L2_SAMPLE", merged.loc[merged._merge.ne("both"), key].head(15).to_dict("records"))
master_only = master.merge(l2[key], on=key, how="left", indicator=True)
print("MASTER_ONLY", int(master_only._merge.eq("left_only").sum()))
print("MASTER_ONLY_GROUP", master_only.loc[master_only._merge.eq("left_only"), "kelompok"].value_counts(dropna=False).to_dict())
print("MATCH_SCOPE", merged.in_scope.value_counts(dropna=False).to_dict())
print("MATCH_GROUP", merged.kelompok.value_counts(dropna=False).to_dict())
print("MATCH_DUP", merged.is_duplikat.value_counts(dropna=False).to_dict())
print("L1_BY_ASSET", pd.crosstab(merged.kode, merged.asset_norm, dropna=False).to_dict())
print("NULL_PER_COL", merged[master.columns.difference(key)].isna().sum().sort_values(ascending=False).head(25).to_dict())
