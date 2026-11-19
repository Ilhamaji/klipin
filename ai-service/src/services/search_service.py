import requests
import os
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

API_URL = os.getenv("SERPAPI_URL", "https://serpapi.com/search")
API_ENGINE = os.getenv("SERPAPI_ENGINE", "google_scholar")
SERPAPI_NUM = int(os.getenv("SERPAPI_NUM", "10"))
SERPAPI_TOP_K = int(os.getenv("SERPAPI_TOP_K", "5"))


def _get_api_key() -> str:
    """Read the SerpAPI key lazily so /ai/summarize still works without it."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError(
            "SERPAPI_KEY belum diatur. Tambahkan ke .env atau environment "
            "sebelum memakai endpoint /ai/search."
        )
    return api_key


def search_serpapi(query: str, embedding_model):

  params = {
      "q": query,
      "engine": API_ENGINE,
      "hl": "id",
      "num": SERPAPI_NUM,
      "as_sdt": "1",
      "api_key": _get_api_key()
  }
  
  response = requests.get(API_URL, params=params, timeout=30)
  
  if response.status_code != 200:
    raise Exception("Gagal mengambil data dari SerpAPI")
  
  data = response.json()
  results = []

  for item in data.get("organic_results", [])[:SERPAPI_NUM]:
    link = item.get("link", "")
    title = item.get("title", "")
    summary = item.get("publication_info", {}).get("summary", "")

    # Skip if explicit book/isbn in title or summary
    if any(kw in (title + " " + summary).lower() for kw in ["isbn", "[book]", "[buku]"]):
        continue

    # Ambil authors — google_scholar returnnya nested
    authors_raw = item.get("publication_info", {}).get("authors", [])
    authors = [a.get("name", "") for a in authors_raw] if authors_raw else []
    
    # Ambil tahun dari summary string jika ada
    year = ""
    if summary:
      # summary biasanya: "A Penulis - Nama Jurnal, 2022 - publisher"
      parts = summary.split(" - ")
      for part in parts:
          for token in part.split(","):
              token = token.strip()
              if token.isdigit() and len(token) == 4:
                  year = token
                  break

    results.append({
        "title": title,
        "link": link,
        "abstract": item.get("snippet", ""),
        "authors": authors,
        "year": year
    })

  # Semantic re-ranking
  ranked_results = semantic_rerank(query, results, embedding_model)
    
  return ranked_results[:SERPAPI_TOP_K]
  
def semantic_rerank(query: str, results: list, embedding_model) -> list:
  if not results:
    return results
  
  # Encode query
  query_embedding = embedding_model.encode(query).reshape(1, -1)
  
  scored_results = []
  
  for item in results:
    # Gabungkan judul + abstrak
    text = f"{item['title']} {item['abstract']}"
    
    # Encode artikel
    article_embedding = embedding_model.encode(text).reshape(1, -1)
    
    # Hitung cosine similarity
    similarity = cosine_similarity(query_embedding, article_embedding)[0][0]
    
    scored_results.append({
      **item,
      "relevance_score": round(float(similarity), 4)
    })
  
  # Urutkan dgn nilai similarity tertinggi
  scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
  
  return scored_results