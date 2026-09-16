# Evaluasi Data Foto Isolator Lombok 2026

Pipeline pemrosesan dan analisis citra untuk evaluasi kelayakan serta pengelompokan foto inspeksi isolator jaringan transmisi tenaga listrik (ULTG Lombok Barat, ULTG Lombok Timur, dan ULTG Sumbawa).

---

## 📌 Gambaran Umum

Sistem ini melakukan triase, klasifikasi, dan pengelompokan foto inspeksi isolator dalam arsitektur multi-lapis:

1. **Lapis 1 (Penyaringan Kelayakan Citra)**
   * Memfilter foto rusak, salah objek, blur, silau, terhalang, terlalu jauh, atau objek terpotong.
   * Modul: `classify_lapis1.py`, `calibrate_lapis1.py`, `analyze_lapis1.py`.

2. **Lapis 2 (Ekstraksi Ciri & Hipotesis Kondisi)**
   * Menilai fokus area isolator, pencatatan ciri terpisah, dan rekonsiliasi terhadap data master.
   * Modul: `classify_lapis2.py`, `prepare_lapis2_fokus.py`, `enrich_lapis2_master.py`, `audit_master_lapis2.py`.

3. **Lapis 3 (Pengelompokan & Similaritas Visual)**
   * Ekstraksi embedding visual (DINOv2), pencarian similaritas (HNSW), verifikasi fitur kunci (ORB), dan relasi graf (NetworkX).
   * Modul: `embed_lapis3_dinov2.py`, `retrieve_lapis3_hnsw.py`, `verify_lapis3_orb.py`, `score_lapis3_relationships.py`, `cluster_lapis3_networkx.py`.

4. **Web Portal & Dashboard Peninjauan**
   * Antarmuka visual interaktif untuk inspeksi hasil, audit keputusan Lapis 1/2/3, dan review manual.
   * Jalankan: `python run_app.py`

---

## 🚀 Memulai (Getting Started)

### 1. Prasyarat
* Python 3.10+
* Git

### 2. Menjalankan Web Portal
```powershell
python run_app.py
```
Akses portal melalui browser di tautan lokal yang ditampilkan di terminal (default: `http://localhost:8080` atau port yang ditentukan).

---

## 📂 Struktur Repositori

* `*.py` — Skrip pipeline pemrosesan Lapis 1, 2, 3, dan aplikasi web portal.
* `portal_assets/` — Aset frontend untuk portal peninjauan.
* `lapis3_config.json` — Konfigurasi parameter embedding dan threshold similaritas.
* `memory.md` — Log arsitektur, parameter, dan status evaluasi.
* `Rencana Impelementasi Olah Foto.txt` — Dokumentasi alur kerja dan rencana implementasi.
