<div align="center">

# 🤖 Klipin AI Service - FastAPI & Machine Learning Microservice
> **Microservice AI Resmi untuk Klasifikasi Kurikulum Merdeka & Peringkasan LLM**

[![English](https://img.shields.io/badge/Language-English-red.svg)](README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-blue.svg)](README.id.md)

</div>

---

Selamat datang di **Repository AI Service** dari **Klipin - Smart Reference & Literature Research System**. Microservice Python FastAPI ini mendukung integrasi pencarian artikel ilmiah (Google Scholar), **Klasifikasi Topik Machine Learning 45-Kelas Kurikulum Merdeka**, ekstraksi teks PDF otomatis, dan peringkasan teks berbasis LLM.

Service ini berjalan sebagai Hugging Face Docker/ZeroGPU Space dan dikonsumsi oleh Klipin Core Backend melalui `/ai/search` dan `/ai/summarize`.

---

## ✨ Kemampuan Utama AI

- **🔍 Crawling Google Scholar**: Memindai artikel akademik via SerpAPI dengan sistem cache kemiripan kata kunci.
- **🧬 Ekstraksi Vektor LaBSE**: Mengubah judul & abstrak menjadi vektor dense 768-dimensi menggunakan `sentence-transformers/LaBSE`.
- **🎯 Klasifikasi Ensemble Multi-Model**: Menguji vektor teks secara simultan pada 4 algoritma (**KNN**, **SVM**, **Logistic Regression**, **Random Forest**) untuk memprediksi subjek (`Biologi`, `Fisika`, `Kimia`, `Matematika`, `IPA`, `IPS`) dan jenjang (`SMA`, `SMP`, `SD`).
- **📄 Deteksi & Ekstraksi PDF Otomatis**: Mendeteksi link PDF naskah (termasuk penerbit OJS) serta memisahkan teks utama dan referensi dengan `PyMuPDF` (`fitz`).
- **🧠 Engine Peringkasan LLM**: Menyintesis dan menerjemahkan dokumen ke Bahasa Indonesia baku terstruktur dalam format JSON via **Groq Cloud API** dengan model **OpenAI GPT-OSS 20B**.
- **⚡ Kompatibilitas ZeroGPU & CPU**: Berjalan lancar di Hugging Face ZeroGPU Spaces (`@spaces.GPU`) maupun eksekusi CPU.

---

## 🧠 Model Peringkasan

Peringkasan berjalan di **Groq** dengan model default `openai/gpt-oss-20b`. Ini menggantikan konfigurasi
sebelumnya yang memakai **LLaMA 3.3 70B Versatile** — model tersebut sudah tidak dipakai di bagian kode mana pun.

| Pengaturan | Nilai | Alasan |
| :--- | :--- | :--- |
| Provider | Groq Cloud API (`/openai/v1/chat/completions`) | Kompatibel OpenAI, tersedia gratis |
| Model default | `openai/gpt-oss-20b` | Bisa diganti lewat env `GROQ_MODEL` |
| `reasoning_effort` | `low` | gpt-oss menghabiskan token tersembunyi untuk reasoning sebelum menjawab; `low` menekan biaya |
| `max_tokens` | `1300` | Cukup untuk ringkasan terstruktur tanpa memotong daftar pustaka |
| Batas konteks | ~1000 kata isi + ~200 kata referensi | PDF panjang dipangkas sebelum dikirim |
| Cache | Per URL artikel | Permintaan ulang untuk naskah yang sama tidak memanggil model lagi |
| Retry | Pada HTTP 429 dan jawaban terpotong | Free tier Groq terkena rate limit; jawaban terpotong dicoba ulang sekali |

Karena keluarannya skema JSON ketat, model diinstruksikan mengisi `judul`, `identitas`, `author`,
`kompetensi`, `isi_materi`, `temuan`, `kesimpulan`, dan `daftar_pustaka`. Semua field itu dijamin ada di
respons meskipun model mengosongkan salah satunya.

> **Catatan soal judul.** gpt-oss sering mengembalikan `judul` kosong. Bila itu terjadi, service mengambil judul
> langsung dari halaman pertama PDF (`_document_title`) alih-alih membiarkan header UI kosong.

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) `0.115.6`, `uvicorn[standard]`
- **Machine Learning & NLP**: PyTorch, `sentence-transformers`, `scikit-learn`, `joblib`, `numpy`
- **Pengolahan Dokumen**: `PyMuPDF` (`fitz`), `beautifulsoup4`, `requests`, `httpx`
- **Integrasi LLM**: Groq Cloud API (`openai/gpt-oss-20b`)
- **Database & ORM**: PostgreSQL (Supabase), `SQLAlchemy`, `psycopg2-binary`
- **UI Space**: Gradio `4.44.0`, `spaces` (decorator ZeroGPU)

### ⚠️ Dependency yang dikunci

Beberapa pin bersifat wajib dan tidak boleh dinaikkan sembarangan:

- **`fastapi==0.115.6` / `starlette==0.41.3`** — pada versi yang lebih baru,
  `APIRouter.include_router()` diam-diam mendaftarkan **nol route**, sehingga `/ai/search` dan
  `/ai/summarize` hilang tanpa pesan error saat startup.
- **`transformers<5` / `huggingface_hub<1.0` / `gradio==4.44.0`** — Gradio 4.44 mengimpor `HfFolder` yang
  dihapus pada `huggingface_hub >= 1.0`. Transformers 5 menuntut `huggingface_hub >= 2.x`, sehingga seluruh
  rantai tetap di 4.x.
- **`scikit-learn<2`** — classifier di `src/models/*.pkl` di-pickle dengan scikit-learn 1.7.x.

---

## ⚙️ Environment Setup & Installation

### 1. Prasyarat
- **Python** v3.10.x atau v3.11.x
- **pip** dan `venv`

### 2. Langkah Instalasi
```bash
# Clone repository
git clone https://github.com/AI-Research-TS/Ai-Services.git
cd Ai-Services

# Buat & aktifkan virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables
Buat file `.env` di root direktori. Daftar lengkapnya ada di `.env.example`:

```env
# API eksternal
SERPAPI_KEY=your_serpapi_key_here
GROQ_API_KEY=your_groq_api_key_here

# Opsional: ganti model peringkasan
# GROQ_MODEL=openai/gpt-oss-20b

# Database (connection pooler Supabase)
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_NAME=your_db_name
DB_PORT=6543

# Cache kemiripan query
SIMILARITY_THRESHOLD=0.85
```

### 4. Menjalankan Server Development
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
Server berjalan di: **`http://127.0.0.1:8000`**

Environment variable diperiksa saat startup — `GROQ_API_KEY` atau `SERPAPI_KEY` yang hilang langsung gagal
dengan jelas, bukan menunggu sampai request pertama.

---

## 🔗 Endpoint API Utama

Terpasang di bawah prefix `/ai`, ditambah health check di root:

| Endpoint | Method | Deskripsi |
| :--- | :--- | :--- |
| `GET /health` | `GET` | Health check ringan (`{"status": "ok"}`). Tidak menyentuh model maupun DB. |
| `POST /ai/search` | `POST` | Crawling artikel via SerpAPI, embedding LaBSE, lalu klasifikasi topik & jenjang. |
| `POST /ai/summarize` | `POST` | Menemukan PDF artikel, mengekstrak teks, dan membuat ringkasan GPT-OSS. |

> Path `/` menyajikan playground Gradio. `/health` adalah endpoint yang dipakai infrastruktur untuk probe —
> endpoint ini menjawab seketika meski model ensemble atau database masih melakukan pemanasan.

### Perilaku saat startup

Pekerjaan berat sengaja dijauhkan dari jalur kritis agar Space langsung melaporkan sehat:

- **Handshake ZeroGPU** dijalankan di hook `startup`, karena aplikasi menyajikan Gradio lewat
  `gr.mount_gradio_app` + `uvicorn` dan tidak pernah memanggil `launch()`. Tanpa ini Space gagal dengan pesan
  *"No @spaces.GPU function detected during startup"*.
- **Auto-migrasi database** berjalan di thread daemon. Sebelumnya proses ini berjalan saat import, sehingga
  port tidak bisa bind sampai Supabase menjawab.

---

## ☁️ Deployment

Service ini di-deploy ke Hugging Face Space. Dua hal wajib diisi di **Space → Settings → Variables and
secrets**: `GROQ_API_KEY` dan `SERPAPI_KEY` (sebagai secrets), ditambah variabel `DB_*`.

```bash
# Push ke remote Space (di lokal terdaftar sebagai `hf`)
git push hf main
```

---

## 👥 Organisasi

Bagian dari **AI-Research-TS** — Klipin Smart Reference & Literature Research System.

| Repository | Peran |
| :--- | :--- |
| [Frontend](https://github.com/AI-Research-TS/Frontend) | Aplikasi web Next.js |
| [Backend](https://github.com/AI-Research-TS/Backend) | API gateway Express.js |
| [Ai-Services](https://github.com/AI-Research-TS/Ai-Services) | Microservice ML & LLM FastAPI (repo ini) |
