import os
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = os.environ.get("BYOKI_RADAR_DB_URL", "sqlite:///./byoki_radar.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class InfectiousDiseaseReport(Base):
    """Store層テーブル (spec section 4/6). validation_status='passed' のみ正式データ。"""

    __tablename__ = "infectious_disease_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    week_number = Column(Integer, nullable=False)
    week_start_date = Column(DateTime, nullable=False)
    prefecture = Column(String, nullable=False)
    region = Column(String, nullable=False)
    disease = Column(String, nullable=False)
    patient_count = Column(Integer, nullable=True)
    per_sentinel_count = Column(Float, nullable=True)
    source_tier = Column(String, nullable=False)  # direct_parse | llm_extract
    source_url = Column(String, nullable=True)
    extracted_by = Column(String, nullable=False)  # pandas | llm
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    validation_status = Column(String, nullable=False)  # passed | flagged
    flag_reason = Column(String, nullable=True)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
