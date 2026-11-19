import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "6543")

try:
    port = int(DB_PORT)
except ValueError:
    port = 6543

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    missing = [
        name
        for name, value in (
            ("DB_USER", DB_USER),
            ("DB_PASSWORD", DB_PASSWORD),
            ("DB_HOST", DB_HOST),
            ("DB_NAME", DB_NAME),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Konfigurasi database AI Service belum lengkap. "
            f"Isi variabel berikut di .env: {', '.join(missing)}. "
            "Alternatifnya, set DATABASE_URL secara langsung."
        )

    DATABASE_URL = (
        f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{port}/{DB_NAME}?sslmode=require"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def run_auto_migration() -> None:
    """Add the model_comparison column if it is missing.

    This is executed once at startup (see app.py). It is kept out of module
    import so that a slow or unreachable database can never delay the process
    from binding its port and serving /health.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE queries ADD COLUMN IF NOT EXISTS model_comparison JSON;"))
            conn.commit()
    except Exception as e:
        print(f"[DB AUTO-MIGRATION NOTICE] {e}")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()