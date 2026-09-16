# Portal Evaluasi Foto Isolator

Jalankan dari terminal mana pun:

```powershell
python "E:\Evaluasi Data Foto Isolator Lombok 2026_ocr_result\run_app.py"
```

Browser terbuka otomatis. Alamat awal adalah `http://127.0.0.1:8501/`. Jika port terpakai, aplikasi mencoba 19 port berikutnya dan mencetak alamat yang tersedia. Tekan `Ctrl+C` pada terminal untuk menghentikan server. Aplikasi hanya menerima koneksi pada komputer lokal.

Pilihan terminal:

```powershell
python run_app.py --port 8600
python run_app.py --no-browser
python run_app.py --prepare-only
python run_app.py --refresh-excel
```

Menu pertama adalah Ringkasan Eksekutif. Menu berikutnya membuka Lapis 1, Lapis 2 aktif, dan Lapis 3. Lapis 1/2 memakai dashboard yang sudah tersimpan. Lapis 3 memakai data yang sama dengan dashboard mandiri, tetapi mengambil bukti pasangan 50 baris per halaman dari indeks SQLite. Semua 368.535 pasangan tetap dapat ditelusuri melalui pilihan Semua pasangan.

Unduhan gabungan berada pada `outputs/portal/Ringkasan_Eksekutif_Lapis_1_2_3.xlsx`:

- `Eksekutif Summary`: indikator, distribusi keputusan, status cluster, dan kelengkapan ciri.
- `Lapis 1`: 26.299 baris foto dengan kode keputusan dan alasan.
- `Lapis 2`: 24.818 baris foto dengan sebelas ciri, kode L1, serta 1.500 penanda sampel audit.
- `Lapis 3`: 2.644 baris anggota pada 941 cluster. Ukuran/skor cluster berulang pada anggotanya. Jangan menjumlahkan ukuran cluster pada sheet ini. Gunakan hitungan cluster unik pada ringkasan.

Excel Lapis 3 lengkap dengan seluruh bukti pasangan tersedia pada menu Lapis 3. Lapis 1 dan Lapis 2 juga mempunyai tautan Excel masing-masing.

Server memakai Python 3.10+ dan standard library. Untuk pemakaian normal, Excel dan indeks yang sudah sesuai sumber akan dipakai kembali. Pembuatan ulang Excel memakai Node dan `@oai/artifact-tool` dari runtime Codex lokal. Aplikasi tidak memasang paket secara otomatis. Pertahankan folder `portal_assets`, `outputs`, serta folder foto di lokasi relatif yang sama dengan `run_app.py`.

Data dibaca saat aplikasi mulai. Setelah hasil analisis diperbarui, hentikan dan jalankan kembali aplikasi. Indeks pasangan dan Excel akan diperbarui bila sumber terkait berubah. Foto asli, keputusan Lapis 1, dan keluaran analisis setiap lapis tidak ditulis ulang oleh portal. Metadata master tidak dimasukkan ke portal atau Excel gabungan.

Verifikasi pengembangan: `portal_assets/verify_portal.py` memeriksa angka sumber, empat sheet, jumlah baris, kode L1, filter, paginasi, dan byte unduhan. Verifier menggunakan Python bundled yang menyediakan `openpyxl`; server tidak memerlukan paket ini.
