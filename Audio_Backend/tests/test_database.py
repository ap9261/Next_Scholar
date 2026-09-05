from sqlalchemy import text
from app.db.database import engine, get_db, init_db
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_database_engine():
    assert engine is not None


def test_init_db():
    init_db()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        assert "audio_files" in tables
        assert "transcripts" in tables
        assert "analysis_results" in tables
        assert "analysis_jobs" in tables
