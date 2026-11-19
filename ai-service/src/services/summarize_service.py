import os
import re
import time
import requests
import fitz
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# KONFIGURASI GROQ API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Model + budget. On Groq's free tier gpt-oss-120b and gpt-oss-20b share the
# same caps (30 RPM / 1000 RPD / 8000 TPM / 200000 TPD), so the real cost
# driver is tokens per request, not the model. 20b is used because it is
# faster and lighter while a long document is in the prompt, and the token
# budget below is trimmed so one summary costs well under the per-minute cap.
# Override with the GROQ_MODEL env var if you want a different model.
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Free-tier Groq is capped at 8000 tokens/min. Measured with o200k_base, the
# prompt boilerplate alone is ~450 tokens, so the document payload is what
# decides throughput. 1000 body words + 200 bibliography words keeps a whole
# request around 1.6k tokens, which fits ~4-5 summaries per minute instead of
# 1-2. Raise these via env if you need longer documents and have more quota.
MAX_BODY_WORDS = int(os.getenv("SUMMARY_MAX_BODY_WORDS", "1000"))
MAX_BIB_WORDS = int(os.getenv("SUMMARY_MAX_BIB_WORDS", "200"))
MAX_OUTPUT_TOKENS = int(os.getenv("SUMMARY_MAX_OUTPUT_TOKENS", "1300"))

# Retry on 429 so a brief burst does not surface as a hard failure.
GROQ_MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", "3"))
GROQ_RETRY_BASE_SECONDS = float(os.getenv("GROQ_RETRY_BASE_SECONDS", "2"))

# HELPER: DETEKSI URL PDF
def _find_pdf_url(article_url: str) -> str | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    if "/article/view/" in article_url:
        download_url = article_url.replace("/article/view/", "/article/download/")
        try:
            test = requests.get(download_url, headers=headers, timeout=10, stream=True)
            if "application/pdf" in test.headers.get("Content-Type", ""):
                return download_url
        except Exception:
            pass

    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        # Jika URL langsung mengarah ke PDF
        if "application/pdf" in response.headers.get("Content-Type", ""):
            return article_url
        # Jika bukan PDF, lakukan parsing HTML untuk mencari link PDF
        soup = BeautifulSoup(response.text, "html.parser")

        pdf_tag = soup.find("a", class_="pdf")
        if pdf_tag and pdf_tag.get("href"):
            href = pdf_tag["href"]
            if not href.startswith("http"):
                href = urljoin(article_url, href)
            return href.replace("/article/view/", "/article/download/") if "/article/view/" in href else href

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if any(kw in href.lower() for kw in [".pdf", "/pdf", "download", "fulltext"]):
                if not href.startswith("http"):
                    href = urljoin(article_url, href)
                return href

    except Exception:
        return None

    return None


# HELPER: EKSTRAKSI TEKS DARI PDF
def _extract_text_from_pdf(pdf_url: str) -> tuple[str, str, str]:
    """Return ``(main_text, raw_bibliography, document_title)``."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(pdf_url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Gagal mengunduh PDF: {str(e)}")

    if "application/pdf" not in response.headers.get("Content-Type", ""):
        raise ValueError("URL tidak mengembalikan file PDF yang valid")

    doc = fitz.open(stream=response.content, filetype="pdf")
    title = _document_title(doc)
    text = "".join([page.get_text() for page in doc])
    doc.close()

    # Memisahkan naskah utama dengan daftar pustaka asli dokumen
    split_pattern = r'\b(daftar pustaka|daftar referensi|references|bibliografi|bibliography)\b'
    parts = re.split(split_pattern, text, flags=re.IGNORECASE)
    
    main_text = parts[0]
    raw_bibliography = ""
    if len(parts) > 2:
        raw_bibliography = "".join(parts[2:])

    # Pembersihan teks utama
    main_text = re.sub(r'\n+', ' ', main_text)
    main_text = re.sub(r'\s+', ' ', main_text).strip()

    words = main_text.split()
    main_text = " ".join(words[:MAX_BODY_WORDS])

    lines = [line for line in main_text.split('. ') if len(line) > 40]
    main_text = '. '.join(lines)

    # Pembersihan teks daftar pustaka kasar (dibatasi agar tidak over-token)
    raw_bibliography = re.sub(r'\n+', ' ', raw_bibliography)
    raw_bibliography = re.sub(r'\s+', ' ', raw_bibliography).strip()
    bib_words = raw_bibliography.split()
    raw_bibliography = " ".join(bib_words[:MAX_BIB_WORDS]) # Batasi agar tidak over-token

    return main_text, raw_bibliography, title


# HELPER: PARSING HASIL RINGKASAN MENJADI BBRP BAGIAN
def _clean_field(value: str) -> str:
    """Trim stray markdown emphasis and whitespace from a parsed field.

    The model often wraps a whole section in bold (``**\\ntext\\n**``), which
    renders as literal ``**`` in the UI. Strip only *wrapping* markers so
    intentional inline bold inside a paragraph is preserved.
    """
    text = value.replace("\r\n", "\n").strip()

    # Remove leading/trailing bold markers, possibly repeated with blank lines.
    while True:
        before = text
        text = re.sub(r"^\s*\*{1,3}\s*", "", text)
        text = re.sub(r"\s*\*{1,3}\s*$", "", text)
        text = text.strip()
        if text == before:
            break

    # Collapse 3+ newlines down to a clean paragraph break.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# Running headers, licence strips and identifiers that sit at the very top of
# a PDF page but are never the article title.
_NOISE_TITLE_PATTERNS = (
    r"^arxiv:\s*\d{4}\.\d{4,5}",
    r"^\s*doi\s*[:.]",
    r"\bissn\b",
    r"\b(isbn|e-?issn|p-?issn)\b",
    r"^creative commons",
    r"^(cc\s*by|licen[cs]e[ds]? under)",
    r"^(copyright|©|\(c\))\s*\d{0,4}",
    r"^(received|accepted|published|available online)\b",
    r"^page \d+",
    r"^(vol\.?|volume|no\.?|nomor)\s*\d",
    r"^journal of\b.{0,60}\b(vol|volume|no)\b",
)


def _is_noise_title(text: str) -> bool:
    lowered = text.lower().strip()
    return any(re.search(p, lowered) for p in _NOISE_TITLE_PATTERNS)


def _clean_title(value: str) -> str:
    """Normalise a document title scraped from PDF metadata or page text."""
    text = re.sub(r"\s+", " ", value or "").strip()
    # Models sometimes echo the placeholder instead of the real value.
    if not text or text.lower() in {"(judul)", "judul", "tidak ada", "n/a", "-", "..."}:
        return ""
    # Long titles are unusable in the UI header; keep the readable head.
    if len(text) > 200:
        text = text[:200].rsplit(" ", 1)[0] + "…"
    return text


def _document_title(doc) -> str:
    """Best-effort title extraction from PDF metadata, falling back to page 1.

    gpt-oss frequently leaves the ``Judul:`` line empty, which showed up as a
    blank header in the summary panel. The PDF itself almost always carries the
    title in its metadata or at the top of the first page, so read it directly
    instead of relying on the model.
    """
    try:
        meta = doc.metadata or {}
    except Exception:
        meta = {}

    title = _clean_title(meta.get("title") or "")
    if title:
        return title

    # Fall back to page 1. Journal PDFs put the article title in the largest
    # topmost text block, but the very first lines are often a running header
    # ("arXiv:1706.03762v7 [cs.CL] 2 Aug 2023") or a copyright strip, so those
    # are skipped. Ranking uses the biggest font first and vertical position
    # second, which keeps the real title ahead of body text with similar size.
    try:
        page = doc[0]
        height = page.rect.height or 1.0
        blocks = page.get_text("dict")["blocks"]
    except Exception:
        return ""

    candidates = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = _clean_title("".join(s.get("text", "") for s in spans))
            if len(text) < 12 or len(text.split()) < 3:
                continue
            if _is_noise_title(text):
                continue
            size = max(s.get("size", 0) for s in spans)
            y = line.get("bbox", (0, 0, 0, 0))[1]
            # Only consider the top half of the first page: article titles live
            # there, while section headings never do.
            if y > height * 0.5:
                continue
            candidates.append((size, -y, text))

    if not candidates:
        return ""

    candidates.sort(reverse=True)
    return candidates[0][2]


def _parse_summary(raw: str) -> dict:
    result = {
        "judul": "",
        "author": "",
        "kompetensi": "",
        "isi_materi": "",
        "temuan": "",
        "kesimpulan": "",
        "daftar_pustaka": ""
    }

    patterns = {
        "judul": r"(?:Judul|Identitas Dokumen):\s*(.*?)(?=Author|Penulis|Kompetensi Utama|$)",
        "author": r"(?:Author|Penulis):\s*(.*?)(?=Kompetensi Utama|$)",
        "kompetensi": r"Kompetensi Utama\s*/\s*Tujuan:\s*(.*?)(?=Isi Materi|$)",
        "isi_materi": r"Isi Materi & Metodologi:\s*(.*?)(?=Inti Pembahasan|$)",
        "temuan": r"Inti Pembahasan & Temuan:\s*(.*?)(?=Kesimpulan|$)",
        "kesimpulan": r"Kesimpulan Keseluruhan:\s*(.*?)(?=Daftar Pustaka|$)",
        "daftar_pustaka": r"Daftar Pustaka:\s*(.*?)$"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match:
            result[key] = _clean_field(match.group(1))

    return result


# CORE: RINGKASAN MENGGUNAKAN GROQ API
def summarize(text: str, raw_bibliography: str = "", document_title: str = "") -> dict:
    if not text.strip():
        return {}

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY tidak ditemukan di environment variables")

    prompt = (
        "Bertindaklah sebagai penulis materi ajar, pakar pendidik, dan asisten peneliti senior. "
        "Tugas Anda adalah menyusun ringkasan yang mendalam, informatif, detail, "
        "dan mudah dipahami dari naskah dokumen yang diberikan.\n"
        "Dokumen ini bisa berupa jurnal ilmiah ataupun materi pembelajaran sekolah.\n"
        "Meskipun naskah asli menggunakan Bahasa Inggris atau bahasa asing lainnya, "
        "Anda WAJIB menuliskan seluruh hasil ringkasan dalam Bahasa Indonesia yang "
        "baku, formal, dan mengalir natural.\n\n"
        "PERATURAN KETAT:\n"
        "1. Bagian Kesimpulan wajib ditulis dalam bentuk PARAGRAF padat (bukan poin-poin).\n"
        "2. Tuliskan kembali daftar pustaka atau referensi penting yang relevan berdasarkan data yang disediakan "
        "di bagian akhir dengan format yang rapi dan teratur.\n\n"
        "Contoh Format output yang digunakan seperti berikut (sesuaikan dengan dokumen atau artikel):\n"
        "Judul: (judul)\n"
        "Author: (nama penulis/author dari dokumen/artikel)\n"
        "Kompetensi Utama / Tujuan: (fokus masalah, tujuan penelitian, atau target kompetensi)\n"
        "Isi Materi & Metodologi: (isi pembahasan pokok, konsep utama, atau metodologi)\n"
        "Inti Pembahasan & Temuan: (fakta penting, data, rumus, atau poin inti materi)\n"
        "Kesimpulan Keseluruhan: (PARAGRAF UTUH, naratif, mengalir, dan tuntas)\n"
        "Daftar Pustaka: (Tuliskan daftar referensi utama yang valid dari dokumen asli)\n\n"
        f"[TEKS NASKAH DOKUMEN]\n{text}\n\n"
        f"[TEKS DAFTAR PUSTAKA ASLI]\n{raw_bibliography if raw_bibliography else 'Tidak terdeteksi pada dokumen.'}"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": MAX_OUTPUT_TOKENS,
        # gpt-oss models spend tokens on hidden "reasoning" before answering.
        # At the default effort that can eat the whole budget and return an
        # empty content, so keep it low for this structured task.
        "reasoning_effort": "low",
    }

    last_error = None
    for attempt in range(GROQ_MAX_RETRIES + 1):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]
            raw = choice["message"]["content"].strip()

            parsed = _parse_summary(raw)
            # Prefer the title read from the PDF itself: the model regularly
            # returns an empty ``Judul:`` line, which left the UI header blank.
            if document_title and not str(parsed.get("judul", "")).strip():
                parsed["judul"] = document_title
            filled = sum(1 for v in parsed.values() if str(v).strip())

            # Guard against a truncated or malformed completion: gpt-oss can
            # burn the budget on reasoning and stop mid-format, which used to
            # come back as a summary with almost every field empty.
            truncated = choice.get("finish_reason") == "length"
            if (truncated or filled < 4) and attempt < GROQ_MAX_RETRIES:
                last_error = f"incomplete summary (filled={filled}/7, finish={choice.get('finish_reason')})"
                continue

            return parsed
        except requests.exceptions.Timeout:
            raise ValueError("Request ke Groq API timeout")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            detail = e.response.text if e.response is not None else str(e)

            # 429 = rate limited. Wait per the Retry-After hint (or back off
            # exponentially) and try again so short bursts stay invisible.
            if status == 429 and attempt < GROQ_MAX_RETRIES:
                wait = GROQ_RETRY_BASE_SECONDS * (2 ** attempt)
                retry_after = None
                if e.response is not None:
                    retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        pass
                time.sleep(min(wait, 20))
                last_error = detail
                continue

            if status == 429:
                raise ValueError(
                    "Kuota Groq API sedang penuh (rate limit). "
                    "Silakan coba lagi dalam beberapa saat."
                )

            if status and status >= 500 and attempt < GROQ_MAX_RETRIES:
                time.sleep(GROQ_RETRY_BASE_SECONDS * (2 ** attempt))
                last_error = detail
                continue

            raise ValueError(f"Groq API mengembalikan error {status}: {detail}")
        except requests.exceptions.RequestException as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                error_detail = e.response.text
            raise ValueError(f"Koneksi gagal ke Groq API: {str(e)} | Detail: {error_detail}")
        except (KeyError, IndexError):
            raise ValueError("Response dari Groq API tidak valid")

    raise ValueError(f"Groq API gagal setelah beberapa percobaan: {last_error}")


# API UTAMA — dipanggil oleh router FastAPI (versi dengan cache ada di bawah)


# ── Ringkasan cache ──────────────────────────────────────────────────
# The same article is frequently summarized more than once (re-opening a
# result, retrying, several users on one class topic). Caching by URL avoids
# spending Groq tokens again for an identical document, which is the cheapest
# possible protection against the free-tier rate limit.
_CACHE_DIR = os.getenv("SUMMARY_CACHE_DIR", "/tmp/summary_cache")
_CACHE_TTL_SECONDS = int(os.getenv("SUMMARY_CACHE_TTL_SECONDS", str(24 * 3600)))


def _cache_path(url: str) -> str:
    import hashlib

    digest = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    return os.path.join(_CACHE_DIR, f"{digest}.json")


def _cache_get(url: str) -> dict | None:
    import json

    path = _cache_path(url)
    try:
        if time.time() - os.path.getmtime(path) > _CACHE_TTL_SECONDS:
            return None
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _cache_put(url: str, value: dict) -> None:
    import json

    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_cache_path(url), "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False)
    except Exception:
        pass  # cache is best-effort, never fail the request over it


def summarize_from_url(article_url: str) -> dict:
    """Cached summarize. Keeps the same signature and response shape."""
    cached = _cache_get(article_url)
    if cached is not None:
        return cached

    pdf_url = _find_pdf_url(article_url)
    if not pdf_url:
        raise ValueError("PDF tidak ditemukan atau artikel di balik paywall")

    text, raw_bibliography, document_title = _extract_text_from_pdf(pdf_url)
    if not text.strip():
        raise ValueError("Gagal mengekstrak teks dari PDF")

    result = summarize(text, raw_bibliography, document_title)
    # The document title is stable, so stamp it even when the model omitted it
    # and the summary came back from the retry path with an empty field.
    if document_title and isinstance(result, dict) and not str(result.get("judul", "")).strip():
        result["judul"] = document_title
    _cache_put(article_url, result)
    return result