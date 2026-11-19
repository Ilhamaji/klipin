<div align="center">

# ⚙️ Klipin Core Backend - Express.js API Gateway
> **Official Backend REST API Microservice for Klipin Reference System**

[![English](https://img.shields.io/badge/Language-English-red.svg)](README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/Language-Bahasa_Indonesia-blue.svg)](README.id.md)

</div>

---

Welcome to the **Core Backend Repository** of **Klipin - Smart Reference & Literature Research System**. This Node.js Express microservice handles user authentication, data persistence via PostgreSQL, personal article bookmarking, and serves as an API Gateway to the Python AI Service (FastAPI / Hugging Face).

---

## ✨ Key Features & API Responsibilities

- **🔐 Authentication & User Security**: User registration, login, JWT token generation, and bcrypt password hashing.
- **⚡ AI Gateway Routing**: Forwards paper search and LLM summarization requests to the Python AI Service, with explicit timeouts so a slow or cold Space cannot hang a request forever.
- **❄️ Cold-Start Tolerance**: Dedicated readiness probe (`/api/ai/ready`) so the frontend can tell "still booting" apart from "broken".
- **💾 PostgreSQL Data Persistence**: Stores users, search histories, saved articles, and notes via Supabase PostgreSQL through Sequelize.
- **🛡️ Request Validation & Middleware**: CORS policy management, JWT authorization, `express-validator` input checks, and centralized error handling.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| Runtime | Node.js v18.x / v20.x |
| Framework | [Express.js](https://expressjs.com/) 4.x |
| Database | PostgreSQL (via [Supabase](https://supabase.com/)) |
| ORM | `sequelize` 6.x + `sequelize-cli` (with `pg`, `pg-hstore`) |
| Authentication | `jsonwebtoken`, `bcrypt` |
| Validation | `express-validator` |
| HTTP Client | `axios` |
| Deployment | [Netlify Functions](https://www.netlify.com/) via `serverless-http` |

---

## ⚙️ Environment Setup & Installation

### 1. Prerequisites
- **Node.js** v18.x or v20.x
- **Yarn** or **npm**
- **PostgreSQL Database** instance

### 2. Installation Steps
```bash
# Clone repository
git clone https://github.com/AI-Research-TS/Backend.git
cd Backend

# Install dependencies
yarn install
```

### 3. Environment Variables Configuration
Create a `.env` file in the root directory (see `.env.example`):

```env
APP_PORT=5000
NODE_ENV=development

# PostgreSQL / Supabase (6543 = Supabase connection pooler)
DB_HOST=your_db_host
DB_PORT=6543
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

# JWT
JWT_SECRET=your_jwt_secret_key

# Python AI Service (Hugging Face Space, direct URL)
FASTAPI_URL=https://iruuuu-ai-service-skripsi.hf.space
```

### 4. Database Migration
```bash
npx sequelize-cli db:migrate
```

### 5. Start Development Server
```bash
yarn dev      # nodemon server.js
# or
yarn start    # node server.js
```
The server will start at: **`http://localhost:5000`**

---

## 🔗 API Endpoints

### Authentication — `/api/auth`

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/api/auth/register` | `POST` | — | Register a new user (validated). |
| `/api/auth/login` | `POST` | — | Log in and receive a JWT. |
| `/api/auth/profile` | `GET` | ✅ | Current user profile. |

### AI Gateway — `/api`

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/api/ai/ready` | `GET` | ✅ | Readiness probe for the AI Space; detects cold starts before the UI waits forever. |
| `/api/search` | `POST` | ✅ | Proxies to `POST /ai/search` on the Python service and stores the query in history. |
| `/api/search/history` | `GET` | ✅ | List search history for the current user. |
| `/api/search/history/:queryId` | `DELETE` | ✅ | Delete one search history entry. |
| `/api/summarize` | `POST` | ✅ | Proxies to `POST /ai/summarize` and returns the structured summary. |

### Notes — `/api/note`

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/api/note` | `GET` | ✅ | List all notes. |
| `/api/note/:id` | `GET` | ✅ | Get a single note. |
| `/api/note/add` | `POST` | ✅ | Create a note. |
| `/api/note/edit/:id` | `PUT` | ✅ | Update a note. |
| `/api/note/delete/:id` | `DELETE` | ✅ | Delete a note. |

### Library — `/api/library`

| Endpoint | Method | Auth | Description |
| :--- | :--- | :--- | :--- |
| `/api/library/saved-articles` | `GET` | ✅ | List saved articles. |
| `/api/library/saved-articles` | `POST` | ✅ | Bookmark an article. |
| `/api/library/saved-articles/:articleId` | `DELETE` | ✅ | Remove a bookmark. |

---

## 🧠 Talking to the AI Service

The Python AI Service runs on Hugging Face Spaces and can be **asleep**. Two safeguards keep this from becoming
a stuck request:

- **Explicit timeouts** on every outbound call (`axios`), including a longer budget for `/summarize`, which waits
  on PDF download + LLM generation.
- **Readiness probe** at `/api/ai/ready`, so the frontend can distinguish "still booting" from "broken" and show
  a clearer message than a generic timeout.

Summarization on the AI side now runs on **Groq `openai/gpt-oss-20b`** (previously LLaMA 3.3 70B). The gateway
does not care which model is used — it forwards the URL and returns the structured summary — but response
latency dropped noticeably with the new model.

---

## ☁️ Deployment

Deployed as a Netlify Function. `netlify.toml` bundles the app through `serverless-http`, with `pg-hstore`
listed in `external_node_modules` so Sequelize's Postgres driver is not stripped from the bundle.

The same environment variables must be set in **Netlify → Site settings → Environment variables**.

---

## 👥 Organization

Part of **AI-Research-TS** — Klipin Smart Reference & Literature Research System.

| Repository | Role |
| :--- | :--- |
| [Frontend](https://github.com/AI-Research-TS/Frontend) | Next.js web application |
| [Backend](https://github.com/AI-Research-TS/Backend) | Express.js API gateway (this repo) |
| [Ai-Services](https://github.com/AI-Research-TS/Ai-Services) | FastAPI ML & LLM microservice |
