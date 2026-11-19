# Dokumentasi Klipin

Dua dokumen PDF siap dibagikan, dibuat dari sumber HTML di folder `src/`.
PDF tidak disimpan di repo; hasilnya di-*generate* sendiri dengan langkah di bawah.

| Dokumen | Sumber | Isi |
| :--- | :--- | :--- |
| Klipin — Deskripsi & Detail Project | `src/01-deskripsi-project.html` | Arsitektur, pipeline AI, performa model, skema DB, API, keamanan, deployment, batasan |
| Klipin — Tutorial Lengkap | `src/02-tutorial-lengkap.html` | Instalasi, database, menjalankan ketiga layanan, uji end-to-end, deploy, ganti sumber artikel / resolver PDF / model summarize, troubleshooting |

## Render ke PDF

Butuh browser berbasis Chromium (Edge atau Chrome). Tidak ada dependensi lain.

Windows PowerShell:

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$src  = (Resolve-Path .\docs\src).Path
$out  = (Resolve-Path .\docs).Path

& $edge --headless=new --disable-gpu --no-pdf-header-footer `
  --print-to-pdf="$out\Klipin-Deskripsi-Project.pdf" `
  "file:///$($src.Replace('\','/'))/01-deskripsi-project.html"

& $edge --headless=new --disable-gpu --no-pdf-header-footer `
  --print-to-pdf="$out\Klipin-Tutorial-Lengkap.pdf" `
  "file:///$($src.Replace('\','/'))/02-tutorial-lengkap.html"
```

Linux / macOS:

```bash
CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser)
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=docs/Klipin-Deskripsi-Project.pdf \
  "file://$PWD/docs/src/01-deskripsi-project.html"
```

`--no-pdf-header-footer` menghapus header tanggal/URL dan nomor halaman bawaan
Chromium. Nomor halaman tidak ditambahkan oleh CSS karena Chromium belum
mendukung `@page { @bottom-center }`.

## Mengedit isi

1. Ubah file HTML di `src/`. Semua gaya ada di blok `<style>` masing-masing file.
2. Render ulang dengan perintah di atas.
3. Cek hasilnya: setiap `<div class="section">` memulai halaman baru.

Panduan singkat gaya:

- `section` — memaksa page break sebelum bagian.
- `callout` / `warn` / `info` — kotak catatan (hijau, kuning, biru).
- `flow > step` — daftar langkah bernomor otomatis.
- `diagram` — blok ASCII dengan font monospace.
- Ukuran kertas dan margin diatur lewat `@page` (A4, margin 16/15/18/15 mm).