# Klipin — AI Research & Reference System

Klipin adalah sistem riset literatur berbasis AI. Pengguna mencari artikel akademik, sistem mengklasifikasikan artikel berdasarkan mata pelajaran dan jenjang, lalu pengguna dapat membuat ringkasan terstruktur dari PDF artikel, menyimpannya sebagai catatan, dan menyimpan artikel ke library pribadi.

**Demo:** [klipin-ts.vercel.app](https://klipin-ts.vercel.app)

Repo ini adalah **monorepo lengkap** yang berisi:

| Folder | Isi | Teknologi |
| :--- | :--- | :--- |
| `frontend/` | UI web | Next.js 16, React 19, Tailwind CSS 4 |
| `backend/` | API gateway, auth, notes, library, proxy AI | Express.js, Sequelize, PostgreSQL |
| `ai-service/` | Pencarian artikel, klasifikasi ML, ekstraksi PDF, ringkasan LLM | FastAPI, scikit-learn, LaBSE, PyMuPDF, Groq |
| `database/` | Skema PostgreSQL untuk instalasi baru | SQL |

---

## Daftar Isi

1. [Arsitektur](#arsitektur)
2. [Fitur](#fitur)
3. [Prasyarat](#prasyarat)
4. [Quick Start](#quick-start)
5. [Konfigurasi Environment](#konfigurasi-environment)
6. [Database](#database)
7. [Menjalankan AI Service](#menjalankan-ai-service)
8. [Menjalankan Backend](#menjalankan-backend)
9. [Menjalankan Frontend](#menjalankan-frontend)
10. [Alur Uji End-to-End](#alur-uji-end-to-end)
11. [API Endpoints](#api-endpoints)
12. [Mengganti Sumber Data Artikel/PDF](#mengganti-sumber-data-artikelpdf)
13. [Deployment](#deployment)
14. [Troubleshooting](#troubleshooting)
15. [Keamanan](#keamanan)
16. [Catatan Perbaikan](#catatan-perbaikan)

---

## Arsitektur

```text
┌────────────────────┐        HTTPS/JSON        ┌────────────────────┐
│  Browser           │ ───────────────────────▶ │  Frontend          │
│  localhost:3000    │                          │  Next.js           │
└────────────────────┘                          └─────────┬──────────┘
                                                          │ /api/*
                                                          ▼
                                               ┌────────────────────┐
                                               │  Backend           │
                                               │  Express :5000     │
                                               │  JWT + PostgreSQL  │
                                               └─────────┬──────────┘
                                                          │ HTTP
                                                          ▼
                                               ┌────────────────────┐
                                               │  AI Service        │
                                               │  FastAPI :7860     │
                                               │  ML + PDF + LLM    │
                                               └──────┬───────┬─────┘
                                                      │       │
                                          ┌───────────┘       └──────────┐
                                          ▼                              ▼
                                  ┌──────────────┐              ┌──────────────┐
                                  │  SerpAPI     │              │  Groq API    │
                                  │  Scholar     │              │  gpt-oss-20b │
                                  └──────────────┘              └──────────────┘

Database: PostgreSQL / Supabase, dipakai backend (Sequelize) dan AI service
(SQLAlchemy) secara bersamaan.
```

**Alur pencarian:**

1. Frontend mengirim `POST /api/search` dengan JWT.
2. Backend memvalidasi user, lalu memanggil `POST /ai/search` di AI service.
3. AI service mengecek cache berdasarkan cosine similarity embedding query.
4. Jika tidak ada cache, AI service mencari 10 hasil Google Scholar via SerpAPI.
5. Hasil di-rerank dengan LaBSE, lalu 5 teratas diklasifikasikan oleh 4 model.
6. Query + artikel disimpan ke PostgreSQL; backend mengembalikan artikel beserta `id` database.
7. Frontend menampilkan artikel; saat pengguna memilih artikel, frontend memanggil `POST /api/summarize`.

---

## Fitur

- Registrasi dan login dengan password hash bcrypt dan JWT 1 hari.
- Pencarian artikel Google Scholar melalui SerpAPI.
- Cache pencarian semantik: query yang mirip tidak memanggil SerpAPI lagi.
- Klasifikasi 45 kelas Kurikulum Merdeka (mata pelajaran + jenjang) memakai KNN, SVM, Logistic Regression, dan Random Forest.
- Ringkasan PDF terstruktur: `judul`, `identitas`, `author`, `kompetensi`, `isi_materi`, `temuan`, `kesimpulan`, `daftar_pustaka`.
- Deteksi PDF langsung, link PDF OJS (`/article/view/` → `/article/download/`), dan link PDF di halaman HTML.
- Catatan pribadi: tambah, lihat, edit, hapus.
- Library/materi tersimpan: simpan, lihat, hapus.
- Riwayat pencarian: lihat dan hapus.
- Ekspor ringkasan ke PDF dari halaman catatan (frontend).
- Health check AI `GET /api/ai/ready` untuk mengurangi kegagalan cold start Hugging Face Space.

---

## Prasyarat

| Kebutuhan | Versi yang disarankan |
| :--- | :--- |
| Node.js | **20 LTS atau 22 LTS** (Next.js 16 minimal Node 20.9) |
| npm | 10+ |
| Python | **3.10 atau 3.11** (model scikit-learn dilatih pada 1.7.x) |
| PostgreSQL | 14+ (Supabase juga bisa) |
| Git + Git LFS | Git 2.40+, Git LFS 3.x |
| Akun | [SerpAPI](https://serpapi.com/), [Groq](https://console.groq.com/), Supabase/PostgreSQL |

> Node 26 dapat menjalankan build, tetapi mode `next dev` di Windows pernah menghasilkan proses node berlebih dan request menggantung. Gunakan Node LTS untuk pengalaman paling stabil.

---

## Quick Start

Ringkasan urutan menjalankan:

```powershell
# 1) Clone (butuh Git LFS untuk model AI)
git lfs install
git clone https://github.com/Ilhamaji/klipin.git
cd klipin
git lfs pull

# 2) Buat database, lalu jalankan database/schema.sql di Supabase SQL Editor

# 3) AI service
cd ai-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# edit .env: SERPAPI_KEY, GROQ_API_KEY, DB_*
uvicorn app:app --host 0.0.0.0 --port 7860 --reload

# 4) Backend (terminal baru)
cd backend
npm ci
Copy-Item .env.example .env
# edit .env: DB_*, JWT_SECRET, FASTAPI_URL=http://localhost:7860
npm start

# 5) Frontend (terminal baru)
cd frontend
npm ci
Copy-Item .env.example .env.local
# edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:5000/api
npm run dev
```

Buka **http://localhost:3000**, daftar akun baru, lalu mulai mencari.

---

## Konfigurasi Environment

### Backend — `backend/.env`

| Variabel | Wajib | Contoh | Keterangan |
| :--- | :---: | :--- | :--- |
| `APP_PORT` | ya | `5000` | Port Express |
| `DB_NAME` | ya | `postgres` | Nama database |
| `DB_USER` | ya | `postgres.xxxxx` | User Supabase |
| `DB_PASSWORD` | ya | `••••••` | Password database |
| `DB_HOST` | ya | `aws-1-ap-southeast-1.pooler.supabase.com` | Host database |
| `DB_PORT` | ya | `6543` | Pooler Supabase; PostgreSQL lokal biasanya `5432` |
| `DB_SSL` | tidak | `true` | `false` hanya untuk PostgreSQL lokal tanpa SSL |
| `JWT_SECRET` | ya | string acak panjang | Jangan gunakan nilai contoh |
| `FASTAPI_URL` | ya | `http://localhost:7860` | URL AI service |
| `AI_TIMEOUT_MS` | tidak | `9000` | Timeout pencarian |
| `AI_SUMMARIZE_TIMEOUT_MS` | tidak | `55000` | Timeout ringkasan |

### AI Service — `ai-service/.env`

| Variabel | Wajib | Contoh | Keterangan |
| :--- | :---: | :--- | :--- |
| `PORT` | tidak | `7860` | Port Uvicorn |
| `SERPAPI_KEY` | ya | `••••••` | API key SerpAPI |
| `SERPAPI_URL` | tidak | `https://serpapi.com/search` | Endpoint sumber artikel |
| `SERPAPI_ENGINE` | tidak | `google_scholar` | Engine SerpAPI |
| `SERPAPI_NUM` | tidak | `10` | Jumlah hasil mentah |
| `SERPAPI_TOP_K` | tidak | `5` | Jumlah hasil akhir |
| `SIMILARITY_THRESHOLD` | tidak | `0.85` | Ambang cache query |
| `GROQ_API_KEY` | ya | `••••••` | API key Groq |
| `GROQ_MODEL` | tidak | `openai/gpt-oss-20b` | Model ringkasan |
| `SUMMARY_MAX_BODY_WORDS` | tidak | `1000` | Batas kata isi PDF |
| `SUMMARY_MAX_BIB_WORDS` | tidak | `200` | Batas kata daftar pustaka |
| `SUMMARY_MAX_OUTPUT_TOKENS` | tidak | `1300` | Batas output LLM |
| `DB_USER` | ya* | `postgres.xxxxx` | User database |
| `DB_PASSWORD` | ya* | `••••••` | Password database |
| `DB_HOST` | ya* | `aws-1-ap-southeast-1.pooler.supabase.com` | Host database |
| `DB_NAME` | ya* | `postgres` | Nama database |
| `DB_PORT` | ya* | `6543` | Port database |
| `DATABASE_URL` | alternatif | `postgresql+psycopg2://...` | Jika diisi, mengalahkan `DB_*` |

\* Wajib jika `DATABASE_URL` tidak diisi.

### Frontend — `frontend/.env.local`

| Variabel | Wajib | Contoh |
| :--- | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | ya | `http://localhost:5000/api` |

`NEXT_PUBLIC_API_URL` boleh berisi host saja (`http://localhost:5000`) atau lengkap dengan `/api`; kode akan menormalkan keduanya.

> **Penting:** jangan commit `.env`, `.env.local`, atau file secrets lain. Semua file tersebut sudah masuk `.gitignore`.

---

## Database

### Opsi A — Supabase (direkomendasikan)

1. Buat project di [Supabase](https://supabase.com/).
2. Buka **SQL Editor**, copy isi [`database/schema.sql`](database/schema.sql), lalu **Run**.
3. Ambil kredensial dari **Project Settings → Database**:
   - Host pooler (biasanya `aws-...pooler.supabase.com`)
   - Port `6543` (transaction pooler)
   - User `postgres.<project-ref>`
   - Password database
4. Isi `backend/.env` dan `ai-service/.env` dengan kredensial yang sama.

### Opsi B — PostgreSQL lokal

```powershell
# Buat database
createdb klipin

# Jalankan skema
psql -d klipin -f database/schema.sql
```

Lalu di `backend/.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_SSL=false
```

Dan di `ai-service/.env`, gunakan `DATABASE_URL`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/klipin?sslmode=disable
```

### Tabel

| Tabel | Fungsi |
| :--- | :--- |
| `users` | Akun pengguna; password bcrypt |
| `notes` | Catatan ringkasan milik pengguna |
| `queries` | Riwayat query + embedding + hasil perbandingan model |
| `articles` | Artikel hasil pencarian, terhubung ke `queries` |
| `saved_articles` | Relasi many-to-many user ↔ artikel yang disimpan |

Relasi utama:

```text
users 1 ── N notes
users 1 ── N queries 1 ── N articles
users 1 ── N saved_articles N ── 1 articles
```

Backend memakai Sequelize dan **tidak** menjalankan `sequelize.sync()`. Karena itu, jalankan `database/schema.sql` lebih dulu. AI service hanya menambahkan kolom `queries.model_comparison` jika belum ada.

---

## Menjalankan AI Service

AI service membutuhkan model `.pkl` yang disimpan di Git LFS:

```powershell
git lfs install
git lfs pull
Get-ChildItem ai-service\src\models\*.pkl | Select-Object Name, Length
```

Ukuran model total sekitar **540 MB** (Random Forest saja ~395 MB). Jika file `.pkl` hanya berukuran beberapa ratus byte, itu pointer LFS dan belum terunduh.

### Instalasi

```powershell
cd ai-service
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Isi minimal:

```env
SERPAPI_KEY=...
GROQ_API_KEY=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_NAME=postgres
DB_PORT=6543
```

### Jalankan

```powershell
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

Cek:

```powershell
curl.exe http://localhost:7860/health
# {"status":"ok","service":"AI-Service-Skripsi"}
```

UI Gradio juga tersedia di `http://localhost:7860/`.

> Jika memakai Hugging Face Space, jangan jalankan `uvicorn` manual; Space menjalankan `app.py` berdasarkan frontmatter `README.md` dan secrets di Settings.

---

## Menjalankan Backend

```powershell
cd backend
npm ci
Copy-Item .env.example .env
notepad .env
npm start
```

Contoh isi `.env` lokal:

```env
APP_PORT=5000
DB_NAME=postgres
DB_USER=postgres.xxxxxxxx
DB_PASSWORD=xxxxxxxx
DB_HOST=aws-1-ap-southeast-1.pooler.supabase.com
DB_PORT=6543
DB_SSL=true
JWT_SECRET=ganti-dengan-string-acak-panjang
FASTAPI_URL=http://localhost:7860
```

Cek:

```powershell
curl.exe http://localhost:5000/
curl.exe http://localhost:5000/api/ai/ready
```

Backend siap jika muncul:

```text
Database connected successfully
Server berjalan! http://localhost:5000
```

---

## Menjalankan Frontend

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
# edit .env.local
npm run dev
```

Isi `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

Buka **http://localhost:3000**. Middleware Next.js akan mengarahkan pengguna yang belum punya cookie `auth_token` ke `/login`.

Build produksi:

```powershell
npm run build
npm start
```

> `next.config.ts` masih memiliki rewrite `/api/:path*` ke backend Netlify sebagai fallback lama. Untuk local, frontend memanggil backend langsung lewat `NEXT_PUBLIC_API_URL`, sehingga rewrite tidak dipakai.

---

## Alur Uji End-to-End

1. Buka `http://localhost:3000/register`, buat akun dengan password minimal 8 karakter, mengandung huruf besar dan angka.
2. Login; pastikan cookie `auth_token` terpasang dan halaman utama terbuka.
3. Cari topik, misalnya `reaksi kimia` atau `fotosintesis`.
4. Tunggu hasil muncul. Jika AI Space baru bangun, backend dapat mengembalikan `503 AI_WARMING_UP`; tunggu ±30 detik lalu coba lagi.
5. Pilih salah satu artikel; panel **Ringkasan Materi** akan memanggil `/api/summarize`.
6. Klik **Simpan ke Catatan**; buka menu **Catatan** untuk melihat hasilnya.
7. Klik ikon simpan pada kartu artikel; buka **Materi** untuk melihat library.
8. Buka **Histori** untuk melihat query dan artikel sebelumnya.
9. Uji edit catatan, hapus catatan, hapus materi, dan logout.

### Contoh uji API dengan `curl.exe`

```powershell
# Register
curl.exe -X POST http://localhost:5000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{"username":"demo_user","password":"DemoPass123"}'

# Login
curl.exe -X POST http://localhost:5000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"demo_user","password":"DemoPass123"}'
```

Simpan `data.token` dari respons login, lalu:

```powershell
$TOKEN = "eyJ..."

curl.exe http://localhost:5000/api/auth/profile -H "Authorization: Bearer $TOKEN"

curl.exe -X POST http://localhost:5000/api/search `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d '{"query":"reaksi kimia"}'

curl.exe -X POST http://localhost:5000/api/summarize `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d '{"url":"https://arxiv.org/pdf/1706.03762"}'
```

---

## API Endpoints

Semua endpoint di bawah `/api`, kecuali `/` dan `/api/ai/ready`, memerlukan header:

```http
Authorization: Bearer <JWT>
```

### Auth

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| POST | `/api/auth/register` | Registrasi |
| POST | `/api/auth/login` | Login, mengembalikan JWT |
| GET | `/api/auth/profile` | Profil user |

### AI Gateway

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/api/ai/ready` | Health/warmup AI (publik) |
| POST | `/api/search` | Cari + klasifikasi artikel |
| GET | `/api/search/history` | Riwayat pencarian |
| DELETE | `/api/search/history/:queryId` | Hapus riwayat |
| POST | `/api/summarize` | Ringkas PDF dari URL |

### Notes

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/api/note` | Semua catatan |
| GET | `/api/note/:id` | Detail catatan |
| POST | `/api/note/add` | Tambah catatan |
| PUT | `/api/note/edit/:id` | Edit `title` dan/atau `contents` |
| DELETE | `/api/note/delete/:id` | Hapus catatan |

### Library

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/api/library/saved-articles` | Artikel tersimpan |
| POST | `/api/library/saved-articles` | Simpan artikel (`{ "articleId": 123 }`) |
| DELETE | `/api/library/saved-articles/:articleId` | Hapus dari library |

### AI Service (langsung, opsional)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/health` | Health check |
| POST | `/ai/search` | `{ "query": "...", "user_id": 1 }` |
| POST | `/ai/summarize` | `{ "url": "https://..." }` |

---

## Mengganti Sumber Data Artikel/PDF

Ada dua lapisan yang bisa diganti:

1. **Sumber metadata artikel** — dari mana judul, abstrak, penulis, tahun, dan link didapat.
2. **Resolver PDF** — dari link artikel, bagaimana memperoleh file PDF yang bisa diekstrak.

### 1. Mengganti sumber metadata artikel

File utama: **`ai-service/src/services/search_service.py`**

Fungsi `search_serpapi(query, embedding_model)` harus mengembalikan daftar dengan bentuk:

```python
[
    {
        "title": "Judul artikel",
        "link": "https://halaman-artikel-atau-pdf",
        "abstract": "Abstrak...",
        "authors": ["Nama 1", "Nama 2"],
        "year": "2024",
        "relevance_score": 0.87,  # diisi oleh semantic_rerank
    }
]
```

Router `ai-service/src/routers/router.py` memakai field berikut:

- `title` → `articles.title`
- `link` → `articles.url`
- `abstract` → `articles.abstract`
- `authors` → `articles.authors`
- `year` → `articles.year`
- `relevance_score` → skor relevansi

#### Contoh: memakai OpenAlex

Tambahkan fungsi baru di `search_service.py`:

```python
import requests

OPENALEX_URL = "https://api.openalex.org/works"

def search_openalex(query: str, embedding_model):
    params = {
        "search": query,
        "per-page": 10,
        "mailto": os.getenv("OPENALEX_MAILTO", ""),
    }
    response = requests.get(OPENALEX_URL, params=params, timeout=30)
    response.raise_for_status()

    results = []
    for work in response.json().get("results", []):
        abstract = ""
        inverted = work.get("abstract_inverted_index") or {}
        if inverted:
            words = []
            for word, positions in inverted.items():
                for position in positions:
                    words.append((position, word))
            abstract = " ".join(word for _, word in sorted(words))

        authors = [
            item.get("author", {}).get("display_name", "")
            for item in work.get("authorships", [])
        ]

        results.append({
            "title": work.get("display_name") or "",
            "link": (
                work.get("primary_location", {}).get("landing_page_url")
                or work.get("doi")
                or ""
            ),
            "abstract": abstract,
            "authors": authors,
            "year": str(work.get("publication_year") or ""),
        })

    return semantic_rerank(query, results, embedding_model)[:5]
```

Lalu ubah import dan pemanggilan di `router.py`:

```python
# dari:
from src.services.search_service import search_serpapi
# menjadi:
from src.services.search_service import search_openalex

# ...
search_results = search_openalex(user_query, embedding_model)
```

Dan ubah label sumber pada respons:

```python
return {
    "source": "openalex",
    # ...
}
```

Cache tetap bekerja karena cache memakai embedding query, bukan nama provider. Pastikan `SERPAPI_KEY` tidak lagi wajib jika Anda sepenuhnya mengganti fungsi pencarian.

#### Contoh provider lain

- **Semantic Scholar**: `https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,abstract,authors,year,url,openAccessPdf`
- **Crossref**: `https://api.crossref.org/works?query=...`
- **CORE**: `https://api.core.ac.uk/v3/search/works`
- **Google Scholar langsung**: hindari scraping HTML karena rawan blokir; gunakan API resmi atau penyedia seperti SerpAPI.

Yang penting: hasil akhir tetap berupa list of dict dengan kontrak di atas, lalu diranking oleh `semantic_rerank`.

### 2. Mengganti sumber/Resolver PDF

File utama: **`ai-service/src/services/summarize_service.py`**

Alur saat ini:

1. `_find_pdf_url(article_url)`:
   - Jika URL adalah halaman OJS `/article/view/`, coba ubah ke `/article/download/`.
   - Jika URL langsung mengembalikan `application/pdf`, pakai URL itu.
   - Jika HTML, cari `<a class="pdf">` atau link yang mengandung `.pdf`, `/pdf`, `download`, `fulltext`.
2. `_extract_text_from_pdf(pdf_url)`:
   - Download PDF dengan header User-Agent.
   - Validasi `Content-Type` adalah `application/pdf`.
   - Ekstrak teks dengan PyMuPDF (`fitz`), pisahkan bagian daftar pustaka.
3. Teks dikirim ke Groq untuk diringkas menjadi JSON.

#### Menambah resolver domain tertentu

Tambahkan cabang sebelum pencarian HTML umum:

```python
def _find_pdf_url(article_url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 ..."}

    # Contoh domain yang punya pola URL sendiri
    if "jurnal.example.ac.id" in article_url:
        pdf_url = article_url.replace("/article/view/", "/article/download/")
        return pdf_url

    # ... kode lama ...
```

Jika server membutuhkan cookie/token:

```python
headers = {
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": article_url,
    "Cookie": os.getenv("JOURNAL_COOKIE", ""),
}
```

#### Menggunakan API resolusi PDF (Unpaywall/Crossref)

Alih-alih menebak link PDF, Anda bisa menyelesaikan DOI ke lokasi open access:

```python
def resolve_pdf_from_doi(doi: str) -> str | None:
    response = requests.get(
        f"https://api.unpaywall.org/v2/{doi}",
        params={"email": os.getenv("UNPAYWALL_EMAIL", "")},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    best = data.get("best_oa_location") or {}
    return best.get("url_for_pdf") or best.get("url")
```

Panggil resolver ini di `_find_pdf_url` jika URL artikel mengandung DOI atau jika link PDF tidak ditemukan.

#### Jika PDF di balik halaman JavaScript

`requests` + BeautifulSoup tidak mengeksekusi JavaScript. Untuk situs seperti itu:

- Cari endpoint PDF di tab Network browser, lalu panggil endpoint tersebut langsung.
- Atau gunakan Playwright/Selenium di AI service untuk membuka halaman dan mengambil URL PDF.
- Atau gunakan API resmi penerbit.

#### Menyesuaikan batas teks

Jika dokumen panjang dan ringkasan terpotong, ubah di `.env`:

```env
SUMMARY_MAX_BODY_WORDS=1500
SUMMARY_MAX_BIB_WORDS=300
SUMMARY_MAX_OUTPUT_TOKENS=1800
```

Naikkan juga kuota Groq; free tier memiliki batas token per menit.

### 3. Mengganti LLM

Default: Groq `openai/gpt-oss-20b` di `summarize_service.py`.

- Ganti model: set `GROQ_MODEL` di `.env`.
- Ganti provider: ubah `GROQ_API_URL`, header Authorization, dan bentuk request/response di fungsi pemanggilan LLM. Format output harus tetap JSON dengan field:
  `judul`, `identitas`, `author`, `kompetensi`, `isi_materi`, `temuan`, `kesimpulan`, `daftar_pustaka`.

### 4. Mengganti URL service, bukan sumber data

- Backend → AI service: `FASTAPI_URL` di `backend/.env`.
- Frontend → backend: `NEXT_PUBLIC_API_URL` di `frontend/.env.local`.
- AI service → SerpAPI: `SERPAPI_URL` + `SERPAPI_ENGINE` di `ai-service/.env`.

---

## Deployment

### Database

Gunakan Supabase. Jalankan `database/schema.sql` di SQL Editor. Simpan host, port, user, password, dan SSL.

### AI Service — Hugging Face Space

1. Buat Space baru (SDK Gradio, Python 3.10).
2. Upload isi folder `ai-service/` (termasuk model LFS).
3. Tambahkan **Secrets**: `SERPAPI_KEY`, `GROQ_API_KEY`, `DB_*`.
4. Pastikan `README.md` di folder AI memiliki frontmatter Space yang benar.
5. Cek `https://<space>.hf.space/health`.

Jika memakai Docker, ubah SDK Space menjadi `docker` dan gunakan `Dockerfile` yang sudah disediakan.

### Backend

Bisa Render, Railway, Fly.io, atau Netlify Functions.

- Set semua env `backend/.env.example`.
- Untuk Netlify, `netlify.toml` dan `netlify/functions/api.js` sudah tersedia.
- Netlify synchronous function memiliki batas ±10 detik. Karena itu `AI_TIMEOUT_MS` default 9000 dan cold start menghasilkan `503 AI_WARMING_UP`.
- Untuk pencarian yang lebih stabil, gunakan Render/Railway dengan timeout lebih panjang.

### Frontend — Vercel

1. Import repo, root directory `frontend`.
2. Set `NEXT_PUBLIC_API_URL=https://<backend-anda>/api`.
3. Deploy.

Jika memakai rewrite internal Next.js, ubah `frontend/next.config.ts`:

```ts
destination: `${process.env.API_PROXY_TARGET}/api/:path*`,
```

lalu set `API_PROXY_TARGET` di environment deployment.

---

## Troubleshooting

| Gejala | Penyebab umum | Solusi |
| :--- | :--- | :--- |
| `503 AI_WARMING_UP` | HF Space cold start | Tunggu 30 detik, ulangi; `GET /api/ai/ready` |
| `502 Gagal mengambil data dari SerpAPI` | Key salah/kuota habis | Cek `SERPAPI_KEY`, kuota SerpAPI |
| `422 PDF tidak ditemukan atau artikel di balik paywall` | Link bukan PDF / butuh login | Coba URL PDF langsung, tambah resolver domain, gunakan API open access |
| `429` / `Kuota Groq API sedang penuh` | Rate limit Groq | Tunggu, kurangi `SUMMARY_MAX_*`, upgrade kuota |
| `401`/`403` | Token tidak ada/kadaluarsa | Login ulang; cek `JWT_SECRET` konsisten |
| `ECONNREFUSED 5000` | Backend mati | Jalankan `npm start` di `backend` |
| `ECONNREFUSED 7860` | AI service mati | Jalankan `uvicorn app:app --port 7860` |
| `Failed to fetch` + CORS | Frontend memanggil URL backend salah | Set `NEXT_PUBLIC_API_URL` ke origin backend yang benar |
| Model `.pkl` kecil | Belum `git lfs pull` | `git lfs install && git lfs pull` |
| `next dev` menggantung / banyak proses | Node terlalu baru / font fetch | Pakai Node 20/22 LTS, coba `npm run build && npm start` |
| Tabel tidak ditemukan | Skema belum dijalankan | Jalankan `database/schema.sql` |
| Supabase `tenant/user not found` | Project paused / kredensial salah | Resume project, cek host/user/password |
| Edit catatan tidak tersimpan | Versi lama memakai `content` vs `contents` | Repo ini sudah memperbaikinya; pastikan memakai kode terbaru |

---

## Keamanan

- **Jangan commit `.env`.** File contoh hanya berisi placeholder.
- Kunci yang pernah tertanam di source lama (SerpAPI dan kredensial Supabase) harus dianggap bocor. **Rotate/revoke** kunci tersebut sebelum deploy.
- Ganti `JWT_SECRET` dengan string acak panjang, misalnya:

  ```powershell
  node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
  ```

- Token GitHub yang dipakai untuk membuat repo ini sebaiknya di-revoke setelah selesai.
- Untuk produksi, batasi CORS di `backend/src/app.js`:

  ```js
  app.use(cors({ origin: process.env.FRONTEND_ORIGIN }));
  ```

- Jangan membuka endpoint AI langsung ke publik tanpa autentikasi tambahan; backend sudah memakai JWT, tetapi AI service sendiri tidak.

---

## Catatan Perbaikan

Repo ini bukan salinan mentah; beberapa perbaikan integrasi sudah diterapkan:

1. **`ai-service/src/services/search_service.py`**: hardcoded SerpAPI key dihapus; sekarang wajib dari `SERPAPI_KEY`. URL/engine/jumlah hasil dapat diatur lewat env.
2. **`ai-service/src/database.py`**: hardcoded kredensial Supabase dihapus; sekarang wajib dari env atau `DATABASE_URL`.
3. **`ai-service/src/schemas.py`**: `model_comparison` ditambahkan ke `SearchResponse` agar tidak dibuang Pydantic.
4. **`backend/src/controllers/note.controller.js`**: edit catatan sekarang menerima `contents` (dan tetap kompatibel dengan `content`); typo `mC` diperbaiki.
5. **`backend/src/controllers/article.controller.js`**: duplicate save → `409`, artikel tidak ditemukan → `404` (bukan `500`).
6. **`backend/src/configs/database.js`**: `DB_SSL=false` didukung untuk PostgreSQL lokal.
7. **`frontend/lib/api.ts`**: endpoint library disesuaikan dengan backend (`/library/saved-articles`, body `articleId`) dan `NEXT_PUBLIC_API_URL` menerima host maupun path `/api`.
8. **`ai-service/app.py`**: duplikasi blok `if __name__ == "__main__"` dihapus.

---

## Kredit

- Model klasifikasi: scikit-learn (KNN, SVM, Logistic Regression, Random Forest)
- Embedding: `sentence-transformers/LaBSE`
- LLM: Groq `openai/gpt-oss-20b`
- Pencarian: SerpAPI Google Scholar

---

Jika ada bagian yang gagal di lingkungan Anda, buka issue dengan menyertakan:

- OS dan versi Node/Python
- Perintah yang dijalankan
- Log backend/AI service
- Status `GET /api/ai/ready`
- Pesan error dari browser console/network tab