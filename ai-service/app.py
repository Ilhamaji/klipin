"""AI Service Skripsi - Gradio UI + REST API on a single Hugging Face Space.

The Gradio UI is mounted at "/" and the FastAPI routers (/ai/*, /health) are
registered on the very same FastAPI application, so this Space serves both a
human-friendly interface and the JSON API consumed by the main backend.

Kept compatible with Gradio 6 (the SDK version configured for this Space).
"""

import os
import json

import gradio as gr
from fastapi import FastAPI

from src.routers.router import router as ai_router
from src.services.summarize_service import summarize_from_url
from src.embed_model import gpu_status

# Groq Cloud - reads from Space secrets / environment variables.
api_key_ok = bool(os.getenv("GROQ_API_KEY"))

STATUS_MESSAGE = (
    "AI Service Online! REST API `/ai/search`, `/ai/summarize` dan `/health` aktif."
)


def status_checker(query_text: str = "") -> str:
    """Small self-check used to verify the Space is alive."""
    if not query_text:
        return STATUS_MESSAGE
    return f"AI Service Online & Siap! Query dites: '{query_text}'"


def summarize_ui(url: str) -> str:
    """Summarize a paper/PDF URL and pretty-print the structured result."""
    url = (url or "").strip()
    if not url:
        raise gr.Error("URL artikel tidak boleh kosong.")
    if not url.startswith(("http://", "https://")):
        raise gr.Error("URL harus dimulai dengan http:// atau https://")
    if not os.getenv("GROQ_API_KEY"):
        raise gr.Error(
            "GROQ_API_KEY belum dikonfigurasi pada Space ini. "
            "Tambahkan sebagai Secret di Settings > Variables and secrets."
        )

    try:
        result = summarize_from_url(url)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        raise gr.Error(f"Gagal meringkas: {exc}") from exc

    if result is None:
        raise gr.Error("Tidak ada hasil ringkasan yang dikembalikan untuk URL tersebut.")

    return "```json\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n```"


with gr.Blocks(title="AI Service Skripsi") as demo:
    gr.Markdown(
        "# 🐠 AI Service Skripsi\n"
        "REST API AI Service aktif dan melayani endpoint `/ai/search`, "
        "`/ai/summarize`, dan `/health`.\n"
        f"GROQ_API_KEY terdeteksi: **{'ya' if api_key_ok else 'tidak'}**"
    )

    with gr.Tab("Status"):
        status_input = gr.Textbox(
            label="Tes query",
            lines=2,
            placeholder="Tes query di sini...",
        )
        status_output = gr.Textbox(label="Hasil", lines=4)
        status_button = gr.Button("Cek Status", variant="primary")
        status_button.click(status_checker, status_input, status_output)
        # Calls the @spaces.GPU marker from a real Gradio event, which is the
        # only context where a ZeroGPU task can be scheduled.
        status_button.click(gpu_status, None, status_output)
        demo.load(status_checker, status_input, status_output)

    with gr.Tab("Summarize"):
        url_input = gr.Textbox(
            label="URL artikel / PDF",
            lines=1,
            placeholder="https://jurnal.example.com/article/view/123",
        )
        summary_output = gr.Markdown(label="Ringkasan")
        summarize_button = gr.Button("Ringkas", variant="primary")
        summarize_button.click(summarize_ui, url_input, summary_output)


# ─────────────────────────────────────────────────────────────
# REST API + Gradio UI on a single FastAPI app.
#
# ORDER MATTERS: gr.mount_gradio_app() installs a catch-all Mount at
# "/{path}". Starlette matches routes in registration order, so anything
# registered *after* the Gradio mount is shadowed and returns 404.
# Therefore the API routes are registered FIRST, then Gradio is mounted
# at "/" to serve the UI and its own untouched sub-paths.
#
# Keeping this in one process is required: the ensemble classifier +
# LaBSE embedder are heavy and must be loaded once, not twice.
# ─────────────────────────────────────────────────────────────
app = FastAPI(title="AI Service Skripsi")

app.include_router(ai_router, prefix="/ai")


@app.get("/health")
def health():
    return {"status": "ok", "service": "AI-Service-Skripsi"}


app = gr.mount_gradio_app(app, demo, path="/")


@app.on_event("startup")
def _startup_tasks() -> None:
    """ZeroGPU startup handshake + DB auto-migration, both off the critical path.

    ZeroGPU: the `spaces` package normally performs its `/startup-report`
    handshake from the first gr.Blocks.launch() call. This app serves Gradio
    via gr.mount_gradio_app + uvicorn and never calls launch(), so the Space
    otherwise fails with "No @spaces.GPU function detected during startup".
    We therefore invoke the same startup hook the SDK would have called.

    DB: the auto-migration used to run at import time in src/database.py and
    blocked the port from binding until Supabase answered. It now runs in a
    daemon thread so the Space reports healthy immediately.
    """
    import threading

    def _zerogpu_handshake() -> None:
        try:
            # spaces.config.Config is a Settings *instance* (not a class).
            import spaces.config as _spaces_config

            if not _spaces_config.Config.zero_gpu:
                return
            # Same call the SDK makes from its gr.Blocks.launch() hook.
            from spaces.zero import startup as _zgpu_startup

            _zgpu_startup()
            print("[startup] ZeroGPU startup report sent")
        except Exception as exc:  # noqa: BLE001 - never block serving the API
            print(f"[startup] ZeroGPU handshake skipped: {exc}")

    def _migrate() -> None:
        from src.database import run_auto_migration

        run_auto_migration()

    threading.Thread(target=_zerogpu_handshake, name="zerogpu-startup", daemon=True).start()
    threading.Thread(target=_migrate, name="db-auto-migration", daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
