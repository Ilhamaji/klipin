FROM python:3.10-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

# app.py exposes `app` (FastAPI + Gradio mounted at "/").
# NOTE: this Space is configured with `sdk: gradio` in README.md, so Hugging
# Face ignores this Dockerfile. It is kept in sync in case the Space is ever
# switched back to `sdk: docker`.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
