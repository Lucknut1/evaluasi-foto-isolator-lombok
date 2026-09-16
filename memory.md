# Memory Proyek Evaluasi Foto Isolator Lombok 2026

Terakhir diperbarui: 13 September 2026

## Tujuan Proyek

Mengolah foto inspeksi isolator berdasarkan dokumen `Rencana Impelementasi Olah Foto.txt`. Lapis 1 menjadi penyaringan awal kelayakan foto. Lapis 2 mencatat ciri foto secara terpisah dan masih berstatus hipotesis otomatis.

Status kerja saat ini: gunakan keluaran `lapis2_20260913` sebagai satu-satunya versi Lapis 2 aktif. `Dataset_master.xlsx` hanya dipakai sebagai guard-rail internal untuk cakupan dan pemilihan sampel audit; metadata master tidak ditampilkan dalam keluaran. Keluaran `lapis2_master_20260913` adalah arsip antara dan bukan keluaran utama. Jangan menggabungkan angka dari arsip dengan versi aktif.

## Sumber Data

| ULTG | Jumlah Foto Aktual |
|---|---:|
| ULTG Lombok Barat | 3.264 |
| ULTG Lombok Timur | 4.102 |
| ULTG Sumbawa | 18.933 |
| **Total** | **26.299** |

`Dataset_master.xlsx` kini menjadi sumber identitas dan cakupan. Master berisi 26.659 baris. Seluruh 26.299 foto yang tersedia cocok satu-ke-satu dengan master memakai kunci ULTG dan nama file. Sebanyak 360 baris master tidak memiliki foto dalam tiga folder sumber. Gunakan 26.299 foto sebagai basis hasil Lapis 1, tetapi gunakan status cakupan master untuk denominator utama Lapis 2.

## Aturan Keputusan Lapis 1

Jika satu foto memenuhi lebih dari satu masalah, gunakan kode dengan prioritas tertinggi berikut:

| Prioritas | Kode | Kategori |
|---:|:---:|---|
| 0 | D | BERKAS_RUSAK |
| 1 | O | SALAH_OBJEK |
| 2 | B | BLUR |
| 3 | K | SILAU |
| 4 | H | TERHALANG |
| 5 | J | TERLALU_JAUH |
| 6 | P | OBJEK_UTAMA_TERPOTONG |
| 7 | L | LAINNYA |
| Lulus | S | SESUAI |

## Status Terkini

Lapis 1 selesai diproses dengan penyaringan visual otomatis yang telah dikalibrasi melalui pemeriksaan sampel. Hasilnya cocok untuk triase dan penentuan antrean pemeriksaan manual. Hasil ini belum menjadi keputusan teknis final untuk evaluasi personel.

### Ringkasan Hasil

| Kode | Jumlah | Persentase |
|:---:|---:|---:|
| S | 22.778 | 86,6% |
| J | 2.845 | 10,8% |
| P | 322 | 1,2% |
| B | 159 | 0,6% |
| K | 110 | 0,4% |
| H | 37 | 0,1% |
| O | 32 | 0,1% |
| D | 16 | 0,1% |
| L | 0 | 0,0% |
| **Total non-S** | **3.521** | **13,4%** |
| **Total foto** | **26.299** | **100,0%** |

### Ringkasan per ULTG

| ULTG | Total | Sesuai | Non-Sesuai | Tingkat Sesuai |
|---|---:|---:|---:|---:|
| Lombok Barat | 3.264 | 2.975 | 289 | 91,1% |
| Lombok Timur | 4.102 | 3.328 | 774 | 81,1% |
| Sumbawa | 18.933 | 16.475 | 2.458 | 87,0% |

Sebanyak 5.363 foto memiliki confidence rendah atau memerlukan tinjauan manual.

## File Hasil Utama

- Excel siap pakai: `outputs/lapis1_20260912_01a095d1/Hasil_Evaluasi_Lapis_1_Foto_Isolator.xlsx`
- Dashboard HTML: `outputs/lapis1_20260912_01a095d1/Dashboard_Evaluasi_Lapis_1_Foto_Isolator.html`

Workbook Excel memuat sheet `Ringkasan`, `Detail Foto`, dan `Panduan Kode`. Dashboard memuat seluruh 26.299 catatan serta menyediakan filter, pencarian, dan paginasi.

## Data Kerja dan Implementasi

Data kerja yang mendasari keluaran:

- `outputs/lapis1_work/hasil_lapis1.csv`
- `outputs/lapis1_work/hasil_lapis1.json`
- `outputs/lapis1_work/summary_lapis1.json`
- `outputs/lapis1_work/metrics_lapis1.csv`

Skrip yang digunakan:

- `analyze_lapis1.py`
- `calibrate_lapis1.py`
- `classify_lapis1.py`
- `inspect_samples.py`
- `measure_borders.py`
- `review_decisions.py`
- `verify_outputs.py`
- `outputs/lapis1_work/artifact_env/build_outputs.mjs`

## Verifikasi yang Sudah Dilakukan

- Workbook berhasil dibuka dan struktur ZIP XLSX valid.
- Workbook berisi 26.299 baris detail foto.
- Pemeriksaan formula tidak menemukan error.
- Dashboard menyematkan 26.299 catatan.
- Filter, pencarian, dan paginasi tersedia pada dashboard.

## Batas Penggunaan dan Risiko

- Hasil otomatis berfungsi sebagai triase, bukan keputusan inspeksi teknis final.
- Foto dengan confidence rendah harus divalidasi manual sebelum angka digunakan untuk KPI personel atau keputusan kinerja.
- Kode P dan O paling sensitif terhadap konteks visual. Kode B dan H juga membutuhkan pemeriksaan sampel.
- Koreksi langsung pada Excel dapat hilang jika keluaran dibuat ulang dari JSON. Tetapkan file koreksi atau mekanisme override sebelum validasi manual skala besar.
- Jangan menjalankan klasifikasi penuh ulang jika aturan dan label tidak berubah. Proses ulang seluruh data akan menambah waktu tanpa meningkatkan kualitas keputusan.

## Urutan Kerja Berikutnya

1. Audit visual 1.500 foto dari kolom `sampel_audit_1500=YA` pada keluaran Lapis 2 aktif. Catat keputusan untuk 11 ciri sesuai dokumen rencana, termasuk nilai yang belum dapat diputuskan.
2. Periksa 135 foto masuk cakupan yang identitas jabatan atau OCR-nya masih perlu cek. Telusuri 65 baris master masuk cakupan tanpa foto secara terpisah sebagai masalah ketersediaan data, bukan mutu foto; informasi ini tidak ditampilkan di keluaran Lapis 2.
3. Validasi manual foto Lapis 1 ber-confidence rendah sebelum memakai kode mutu sebagai KPI. Ukur kesalahan per ciri, kode Lapis 1, dan ULTG pada sampel audit.
4. Simpan koreksi dalam file override terpisah dengan kunci ULTG dan nama file, identitas penilai, tanggal, dan alasan. Jangan hanya mengubah workbook hasil.
5. Bangun ulang Excel dan dashboard setelah koreksi disahkan. Sampai saat itu, semua label visual Lapis 2 tetap hipotesis otomatis, bukan hasil inspeksi final.

## Lapis 2: Hasil Awal per 13 September 2026

- Ruang lingkup: seluruh 26.299 foto, 11 kolom ciri sesuai dokumen rencana.
- Metode: pemetaan proksi dari keputusan dan metrik visual Lapis 1. Belum ada anotasi visual manual untuk Lapis 2.
- Sampel audit: 1.500 foto terpilih secara deterministik dan terstratifikasi menurut ULTG serta kode Lapis 1. Jumlah per ULTG: Lombok Barat 361, Lombok Timur 404, Sumbawa 735.
- Sebanyak 25.903 foto memiliki sedikitnya satu ciri `belum_dinilai`. Totalnya 46.760 sel ciri. Nilai ini bukan nol dan bukan berarti tidak ada objek.
- `bahan_isolator` selalu `tidak_jelas`. Warna agregat tidak cukup untuk membedakan bahan isolator dari warna tower atau vegetasi.
- `jumlah_renteng_terbaca` sering `belum_dinilai`. Geometri kandidat tidak membuktikan jumlah renteng yang piringannya benar-benar terbaca.
- `ragu2` otomatis adalah penanda keputusan dekat ambang, bukan pengakuan ragu dari penilai manusia.
- Arah, halangan, isi frame, bagian renteng, cahaya, ketajaman, dan noise adalah estimasi metrik. Distribusinya belum layak dijadikan KPI personel atau inventaris aset final.

Keluaran terpisah dari Lapis 1:

- Excel: `outputs/lapis2_20260913/Hasil_Evaluasi_Lapis_2_Foto_Isolator.xlsx`
- Dashboard HTML: `outputs/lapis2_20260913/Dashboard_Evaluasi_Lapis_2_Foto_Isolator.html`
- Data kerja: `outputs/lapis2_work/hasil_lapis2.csv`, `hasil_lapis2.json`, dan `summary_lapis2.json`.
- Implementasi: `classify_lapis2.py` dan `outputs/lapis2_work/build_lapis2.mjs`.

Excel berisi `Ringkasan Lapis 2`, `Ciri per Foto`, dan `Panduan dan Batas`. Dashboard memiliki pilihan ciri, filter ULTG, kode Lapis 1, sampel audit, nilai ciri, status celah, pencarian foto, dan tautan ke foto asli. Pemeriksaan struktur XLSX, jumlah detail, alokasi sampel, total celah, serta uji filter dashboard telah berhasil. Keluaran Lapis 1 tetap utuh.

Langkah operasional berikutnya ialah mengaudit 1.500 foto terpilih, menyimpan koreksi pada file override terpisah, menghitung akurasi per ciri dan per strata, lalu membangun ulang Lapis 2. Jangan mengubah Excel hasil saja karena perubahan tidak akan terbawa pada regenerasi.

## Guard-rail Master dan Revisi Lapis 2 per 13 September 2026

- `Dataset_master.xlsx` digunakan hanya secara internal untuk mencocokkan kunci `ULTG + nama_file`, menentukan 24.818 foto masuk cakupan, dan memilih sampel audit 1.500 foto secara terstratifikasi.
- Metadata master, baris master tanpa foto, dan foto di luar cakupan tidak ditampilkan dalam keluaran Lapis 2 aktif.
- Sebelas ciri Lapis 2 tetap hipotesis dari proksi metrik Lapis 1. Kode Lapis 1 disalin apa adanya sebagai konteks dan ditabulasikan hubungannya dengan setiap ciri; Lapis 2 tidak menghitung ulang atau mengubah keputusan Lapis 1.
- Di antara 24.818 foto aktif, 24.444 memiliki sedikitnya satu ciri `belum_dinilai`, dengan 44.131 sel ciri belum dinilai.

Keluaran aktif yang diperbarui:

- Excel: `outputs/lapis2_20260913/Hasil_Evaluasi_Lapis_2_Foto_Isolator.xlsx`. Sheet: `Ringkasan Lapis 2`, `Ciri per Foto`, `Hubungan Kode L1`, `Panduan dan Batas`.
- Dashboard: `outputs/lapis2_20260913/Dashboard_Evaluasi_Lapis_2_Foto_Isolator.html`.
- Data kerja: `outputs/lapis2_work/hasil_lapis2.csv`, `hasil_lapis2.json`, dan `summary_lapis2.json`.
- Guard-rail internal: `outputs/lapis2_work/guardrail_internal.json`; file ini bukan bagian dari output publik.
- Implementasi: `prepare_lapis2_fokus.py`, `classify_lapis2.py`, dan `outputs/lapis2_work/build_lapis2.mjs`.

Verifikasi revisi: data kerja berisi 24.818 baris dan 1.500 sampel; relasi tersedia untuk 11 ciri; XLSX valid dengan empat sheet tanpa kolom master dan tanpa error formula; dashboard menyematkan 24.818 catatan tanpa metadata master. Hash keluaran Lapis 1 cocok dengan hash guard-rail sehingga Lapis 1 tidak berubah. `outputs/lapis2_master_20260913` dan `outputs/lapis2_master_work` dipertahankan sebagai arsip internal, bukan rujukan output aktif.

Catatan penting: `summary_lapis2.json` dan hasil aktif memakai denominator 24.818 foto masuk cakupan. Jangan menggabungkannya dengan arsip Lapis 2 awal yang memakai 26.299 foto atau dengan keluaran master-facing lama.

## Lapis 2 Arsip Awal per 13 September 2026

Keluaran `outputs/lapis2_work/sebelum_fokus_20260913` menyimpan snapshot sebelum guard-rail master diterapkan: 26.299 foto dan sampel lama 1.500 foto. Snapshot ini hanya untuk reproduksibilitas dan pembanding, bukan keluaran aktif.

- Excel dan dashboard aktif sudah diperbarui dengan menimpa file pada `outputs/lapis2_20260913`.
- Hasil Lapis 1 tetap utuh dan tidak ditulis ulang.
- Hubungan ciri dengan kode Lapis 1 bersifat deskriptif; tidak menyatakan akurasi ciri dan tidak mengubah kode keputusan.
## Lapis 3: Implementasi Bertahap per 13 September 2026

Lapis 3 diimplementasikan terpisah dari Lapis 1 dan Lapis 2 dengan urutan aman: `DINOv2 embedding → HNSW Top-K → ORB verification → relationship table → NetworkX cluster → cluster validation`. Tujuannya membentuk relasi antar foto dan cluster yang dapat diaudit, bukan mengubah keputusan mutu foto.

- Konfigurasi: `lapis3_config.json`; model awal `facebook/dinov2-small`, Top-K 20, bobot dan threshold dapat diubah tanpa mengedit logika pipeline.
- Tahap 1: `embed_lapis3_dinov2.py` membaca `outputs/lapis2_work/hasil_lapis2.csv`, menghitung hash file, pHash/dHash, dan menyiapkan cache embedding ter-normalisasi L2.
- Tahap 2: `retrieve_lapis3_hnsw.py` menggunakan HNSW cosine dan menolak fallback brute-force O(N²).
- Tahap 3: `verify_lapis3_orb.py` menghitung evidence pHash/dHash, ORB, Lowe ratio, dan homography/RANSAC.
- Tahap 4: `score_lapis3_relationships.py` menghasilkan skor, confidence, tipe `EXACT_DUPLICATE`, `NEAR_DUPLICATE`, `SAME_CAPTURE`, `SAME_OBJECT`, `RELATED_ONLY`, atau `UNRELATED`.
- Tahap 5-6: `cluster_lapis3_networkx.py` membentuk connected components, memilih canonical image, dan memberi status `VALID`, `NEED_REVIEW`, atau `SPLIT_RECOMMENDED` untuk mencegah similarity chaining dianggap final.
- Builder `outputs/lapis3_work/build_lapis3.mjs` dan verifier `verify_lapis3_outputs.py` telah disiapkan. Builder memiliki filter status cluster, tipe relationship, confidence, kode L1 canonical, ULTG, pencarian, ringkasan score band, tabel evidence, thumbnail anggota, dan workbook terpisah.

Status final: seluruh enam tahap Lapis 3 selesai dan lulus verifikasi pada 13 September 2026. Tahap 1 menghasilkan embedding 24.818 foto (`embeddings.npy`, 384 dimensi, ternormalisasi L2). Tahap 2 menghasilkan 368.535 candidate pairs. Tahap 3 memverifikasi 368.535/368.535 pair dengan `orb_status=OK`. Tahap 4 menghasilkan `pair_relationships.csv/json` sebanyak 368.535 baris dengan 13.519 edge non-`UNRELATED` sebelum threshold clustering dan 2.454 edge yang dipakai graph pada threshold 0,70. Tahap 5-6 menghasilkan 941 cluster dan 2.644 anggota cluster: 3 `VALID`, 122 `NEED_REVIEW`, dan 816 `SPLIT_RECOMMENDED`. Verifier proyek `verify_lapis3_outputs.py` PASS.

Output final Lapis 3 berada di `outputs/lapis3_20260913`: `Hasil_Evaluasi_Lapis_3_Relasi_Duplikasi_Foto_Isolator.xlsx` dan `Dashboard_Evaluasi_Lapis_3_Relasi_Duplikasi_Foto_Isolator.html`. Audit tersimpan di `outputs/lapis3_work/stage3_orb_audit_20260913.json`, `stage4_relationship_audit_20260913.json`, `stage5_cluster_audit_20260913.json`, dan `stage6_final_validation_20260913.json`.

Sebelum dependency lengkap, belum ada output Lapis 3 yang sah berupa embedding penuh, candidate pair, verified pair, relationship, cluster, workbook, atau dashboard. Jangan mencatat jumlah hasil atau membuka dashboard Lapis 3 sebelum seluruh pipeline diverifikasi.
</functions.Edit}myzyň? nope. Need proper JSON no typo. I accidentally wrote malformed tool call? Let's see. I invoked with weird. It may be invalid? It output nothing maybe not run? Need check? Actually assistant to=functions.Edit is shown maybe no result? It appears tool call malformed because content had 
Batas penting: Lapis 3 tidak menulis keluaran Lapis 1/Lapis 2. GPS dan waktu tetap nullable; jangan mengklaim evidence tersebut tersedia tanpa EXIF. Hasil relasi dan cluster otomatis adalah hipotesis audit, bukan keputusan inspeksi final.

## Portal Localhost Lapis 1, 2, dan 3

- Status: selesai dan sudah diuji. Pada pemeriksaan terakhir 13 September 2026, server dijalankan kembali melalui `python run_app.py --no-browser` dan tersedia di `http://127.0.0.1:8501/`.
- Entry point: `run_app.py`. Jalankan `python run_app.py` dari direktori proyek, atau gunakan path absolut skrip dari direktori lain. Python 3.10+.
- Alamat awal: `http://127.0.0.1:8501/`. Bila port terpakai, aplikasi memilih port berikutnya dan mencetak alamat aktual. Server hanya bind loopback. `Ctrl+C` menghentikan server.
- Empat menu berurutan: Ringkasan Eksekutif, Lapis 1, Lapis 2 aktif, dan Lapis 3. Ringkasan adalah tampilan awal. Master tidak ditampilkan.
- Lapis 1/2 memakai dashboard tersimpan. Lapis 3 memakai halaman ringan dengan filter cluster, thumbnail anggota, dan bukti pasangan berpaginasi 50 baris. Seluruh 368.535 pasangan tetap tersedia melalui pilihan Semua pasangan.
- Excel gabungan: `outputs/portal/Ringkasan_Eksekutif_Lapis_1_2_3.xlsx`. Empat sheet: `Eksekutif Summary`, `Lapis 1` (26.299 foto), `Lapis 2` (24.818 foto), dan `Lapis 3` (2.644 anggota dari 941 cluster).
- Grain sheet Lapis 3 adalah satu baris per anggota. Ukuran/skor cluster berulang pada anggota; hitung cluster unik, jangan menjumlahkan ukuran berulang. Seluruh bukti pasangan terdapat pada Excel Lapis 3 lengkap yang tersedia dari menu Lapis 3.
- File pendukung: `portal_assets/index.html`, `lapis3.html`, `build_executive.mjs`, `README.md`, dan `verify_portal.py`. Indeks dan manifest cache berada di `outputs/portal_work`.
- Pemakaian server memakai standard library Python. Regenerasi Excel memakai runtime Node/Artifact Tool lokal; tidak ada instalasi paket otomatis. Jalankan ulang aplikasi setelah data sumber berubah.
- Verifikasi: sumber dan angka ringkasan cocok, empat sheet dan jumlah baris benar, byte unduhan cocok dengan berkas, hash Lapis 1 tetap sama, filter serta paginasi pasangan lolos. Keempat menu, filter VALID, hasil kosong, reset, dan penelusuran semua pasangan telah diperiksa di browser.

Server harus tetap berjalan agar localhost dapat diakses. Setelah terminal ditutup atau komputer dimulai ulang, jalankan kembali `python run_app.py`. File Excel tetap tersimpan dan dapat dibuka tanpa server.

## Log Pembaruan

- 12 September 2026: Dokumen rencana dibaca, inventaris foto dihitung, Lapis 1 dijalankan, hasil Excel dan dashboard dibuat, lalu keluaran diverifikasi.
- 12 September 2026: `memory.md` dibuat untuk menjaga konteks, keputusan, risiko, dan kelanjutan pekerjaan.
- 13 September 2026: Lapis 2 awal dibuat dalam Excel dan dashboard terpisah. Semua 26.299 foto dicakup; 1.500 foto disiapkan untuk audit visual. Batas inferensi dicatat secara eksplisit.
- 13 September 2026: Lapis 2 sempat direkonsiliasi ulang dengan `Dataset_master.xlsx` dalam keluaran terpisah bertema master. Keluaran tersebut kini menjadi arsip antara, bukan keluaran utama.
- 13 September 2026: Lapis 2 aktif diperbarui pada `outputs/lapis2_20260913` dengan master sebagai guard-rail internal saja. Denominator aktif menjadi 24.818 foto masuk cakupan, sampel audit 1.500 foto, metadata master tidak ditampilkan, dan hubungan ciri dengan kode Lapis 1 ditampilkan secara deskriptif.
- 13 September 2026: Verifikasi revisi menunjukkan data kerja 24.818 baris, sampel audit 1.500, relasi 11 ciri terhadap kode L1 tersedia, XLSX valid tanpa error formula, dashboard berisi 24.818 catatan tanpa metadata master, dan hash Lapis 1 tetap cocok/tidak berubah.
- 13 September 2026: Tahap 4-6 Lapis 3 selesai. Relationship scoring menghasilkan 368.535 baris dan 13.519 edge non-UNRELATED; NetworkX menghasilkan 941 cluster dan 2.644 anggota; validasi final PASS. Output final ada di `outputs/lapis3_20260913`, dan `verify_lapis3_outputs.py` mengembalikan PASS.
- 13 September 2026: Portal `run_app.py` selesai dengan empat menu dan unduhan Excel gabungan empat sheet. Pemeriksaan ulang `portal_assets/verify_portal.py` menghasilkan PASS untuk total sumber, sheet dan baris detail, keutuhan kode Lapis 1, filter, paginasi, kecocokan byte unduhan, dan pembatasan akses file internal. Server aktif pada port 8501 saat serah terima.
