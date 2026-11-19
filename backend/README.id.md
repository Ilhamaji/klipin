<div align="center">

# ⚙️ Klipin Core Backend - Express.js API Gateway
> **Microservice REST API Resmi untuk Klipin Reference System**

[![English](https://img.shields.io/badge/Language-English-red.svg)](README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-blue.svg)](README.id.md)

</div>

---

Selamat datang di **Repository Core Backend** dari **Klipin - Smart Reference & Literature Research System**. Microservice Node.js Express ini menangani autentikasi pengguna, penyimpanan data di PostgreSQL, penandaan artikel, serta berperan sebagai API Gateway ke Python AI Service (FastAPI / Hugging Face).

---

## ✨ Fitur Utama & Tanggung Jawab API

- **🔐 Autentikasi & Keamanan Pengguna**: Registrasi, login, pembuatan token JWT, dan hashing password dengan bcrypt.
- **⚡ Gateway AI**: Meneruskan permintaan pencarian artikel dan peringkasan LLM ke Python AI Service, dengan timeout eksplisit agar Space yang lambat atau cold start tidak menggantung request selamanya.
- **❄️ Toleransi Cold Start**: Endpoint probe `/api/ai/ready` agar frontend bisa membedakan "masih booting" dari "rusak".
- **💾 Persistensi PostgreSQL**: Menyimpan pengguna, riwayat pencarian, artikel tersimpan, dan catatan lewat Supabase PostgreSQL dengan Sequelize.
- **🛡️ Validasi & Middleware**: Pengaturan kebijakan CORS, otorisasi JWT, validasi input `express-validator`, dan penanganan error terpusat.

---

## 🛠️ Tech Stack

| Lapisan | Teknologi |
| :--- | :--- |
| Runtime | Node.js v18.x / v20.x |
| Framework | [Express.js](https://expressjs.com/) 4.x |
| Database | PostgreSQL (via [Supabase](https://supabase.com/)) |
| ORM | `sequelize` 6.x + `sequelize-cli` (dengan `pg`, `pg-hstore`) |
| Autentikasi | `jsonwebtoken`, `bcrypt` |
| Validasi | `express-validator` |
| HTTP Client | `axios` |
| Deployment | [Netlify Functions](https://www.netlify.com/) via `serverless-http` |

---

## ⚙️ Environment Setup & Installation

### 1. Prasyarat
- **Node.js** v18.x atau v20.x
- **Yarn** atau **npm**
- Instance **PostgreSQL**

### 2. Langkah Instalasi
```bash
# Clone repository
git clone https://github.com/AI-Research-TS/Backend.git
cd Backend

# Install dependencies
yarn install
```

### 3. Konfigurasi Environment Variables
Buat file `.env` di root direktori (lihat `.env.example`):

```env
APP_PORT=5000
NODE_ENV=development

# PostgreSQL / Supabase (6543 = connection pooler Supabase)
DB_HOST=your_db_host
DB_PORT=6543
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

# JWT
JWT_SECRET=your_jwt_secret_key

# Python AI Service (Hugging Face Space, URL langsung)
FASTAPI_URL=https://iruuuu-ai-service-skripsi.hf.space
```

### 4. Migrasi Database
```bash
npx sequelize-cli db:migrate
```

### 5. Menjalankan Server Development
```bash
yarn dev      # nodemon server.js
# atau
yarn start    # node server.js
```
Server berjalan di: **`http://localhost:5000`**

---

## 🔗 Endpoint API

### Autentikasi — `/api/auth`

| Endpoint | Method | Auth | Deskripsi |
| :--- | :--- | :--- | :--- |
| `/api/auth/register` | `POST` | — | Registrasi pengguna baru (dengan validasi). |
| `/api/auth/login` | `POST` | — | Login dan menerima JWT. |
| `/api/auth/profile` | `GET` | ✅ | Profil pengguna aktif. |

### Gateway AI — `/api`

| Endpoint | Method | Auth | Deskripsi |
| :--- | :--- | :--- | :--- |
| `/api/ai/ready` | `GET` | ✅ | Probe kesiapan AI Space; mendeteksi cold start sebelum UI menunggu terlalu lama. |
| `/api/search` | `POST` | ✅ | Meneruskan ke `POST /ai/search` di Python service dan menyimpan query ke riwayat. |
| `/api/search/history` | `GET` | ✅ | Daftar riwayat pencarian pengguna. |
| `/api/search/history/:queryId` | `DELETE` | ✅ | Hapus satu entri riwayat pencarian. |
| `/api/summarize` | `POST` | ✅ | Meneruskan ke `POST /ai/summarize` dan mengembalikan ringkasan terstruktur. |

### Catatan — `/api/note`

| Endpoint | Method | Auth | Deskripsi |
| :--- | :--- | :--- | :--- |
| `/api/note` | `GET` | ✅ | Daftar seluruh catatan. |
| `/api/note/:id` | `GET` | ✅ | Detail satu catatan. |
| `/api/note/add` | `POST` | ✅ | Buat catatan baru. |
| `/api/note/edit/:id` | `PUT` | ✅ | Ubah catatan. |
| `/api/note/delete/:id` | `DELETE` | ✅ | Hapus catatan. |

### Library — `/api/library`

| Endpoint | Method | Auth | Deskripsi |
| :--- | :--- | :--- | :--- |
| `/api/library/saved-articles` | `GET` | ✅ | Daftar artikel tersimpan. |
| `/api/library/saved-articles` | `POST` | ✅ | Simpan artikel. |
| `/api/library/saved-articles/:articleId` | `DELETE` | ✅ | Hapus artikel tersimpan. |

---

## 🧠 Komunikasi dengan AI Service

Python AI Service berjalan di Hugging Face Spaces dan bisa **tertidur**. Dua pengaman mencegah request
menggantung:

- **Timeout eksplisit** pada setiap panggilan keluar (`axios`), termasuk anggaran lebih panjang untuk
  `/summarize` yang menunggu unduhan PDF + generasi LLM.
- **Readiness probe** di `/api/ai/ready`, sehingga frontend dapat membedakan "masih booting" dari "rusak" dan
  menampilkan pesan yang lebih jelas daripada timeout generik.

Peringkasan di sisi AI kini memakai **Groq `openai/gpt-oss-20b`** (sebelumnya LLaMA 3.3 70B). Gateway tidak
peduli model apa yang dipakai — ia hanya meneruskan URL dan mengembalikan ringkasan terstruktur — namun latensi
respons menurun cukup terasa dengan model baru.

---

## ☁️ Deployment

Di-deploy sebagai Netlify Function. `netlify.toml` membundel aplikasi lewat `serverless-http`, dengan
`pg-hstore` didaftarkan di `external_node_modules` agar driver Postgres Sequelize tidak terbuang dari bundle.

Environment variable yang sama wajib diisi di **Netlify → Site settings → Environment variables**.

---

## 👥 Organisasi

Bagian dari **AI-Research-TS** — Klipin Smart Reference & Literature Research System.

| Repository | Peran |
| :--- | :--- |
| [Frontend](https://github.com/AI-Research-TS/Frontend) | Aplikasi web Next.js |
| [Backend](https://github.com/AI-Research-TS/Backend) | API gateway Express.js (repo ini) |
| [Ai-Services](https://github.com/AI-Research-TS/Ai-Services) | Microservice ML & LLM FastAPI |
