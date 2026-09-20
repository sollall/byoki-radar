from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, InfectiousDiseaseReport
from app.extract import PARSERS
from app.masters import PER_SENTINEL_MAX
from app.schemas import RawRecord
from app.validation import validate_record, validate_records
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_raw(**overrides) -> RawRecord:
    defaults = dict(
        year=2025,
        week_number=20,
        week_start_date=datetime(2025, 5, 12),
        prefecture="京都府",
        region="南・伏見",
        disease="インフルエンザ",
        patient_count=10,
        per_sentinel_count=2.5,
        source_tier="direct_parse",
        source_url="http://example.test",
        extracted_by="pandas",
    )
    defaults.update(overrides)
    return RawRecord(**defaults)


def test_valid_record_passes():
    v = validate_record(make_raw())
    assert v.validation_status == "passed"
    assert v.disease == "influenza"


def test_unknown_region_is_flagged_and_not_renamed():
    v = validate_record(make_raw(region="謎の管区"))
    assert v.validation_status == "flagged"
    assert v.region == "謎の管区"  # 推測で丸めない
    assert "unknown_region" in v.flag_reason


def test_unknown_disease_is_flagged():
    v = validate_record(make_raw(disease="謎の感染症"))
    assert v.validation_status == "flagged"
    assert "unknown_disease" in v.flag_reason


def test_per_sentinel_out_of_range_is_flagged():
    v = validate_record(make_raw(per_sentinel_count=PER_SENTINEL_MAX + 1))
    assert v.validation_status == "flagged"
    assert "per_sentinel_count_out_of_range" in v.flag_reason

    v_negative = validate_record(make_raw(per_sentinel_count=-1))
    assert v_negative.validation_status == "flagged"


def test_week_over_week_spike_is_flagged():
    session = make_session()
    session.add(
        InfectiousDiseaseReport(
            year=2025,
            week_number=19,
            week_start_date=datetime(2025, 5, 5),
            prefecture="京都府",
            region="南・伏見",
            disease="influenza",
            patient_count=4,
            per_sentinel_count=1.0,
            source_tier="direct_parse",
            source_url=None,
            extracted_by="pandas",
            fetched_at=datetime.utcnow(),
            validation_status="passed",
        )
    )
    session.commit()

    v = validate_record(make_raw(per_sentinel_count=15.0), session=session)
    assert v.validation_status == "flagged"
    assert "week_over_week_spike" in v.flag_reason


def test_conflicting_duplicate_extraction_is_flagged():
    session = make_session()
    records = [make_raw(per_sentinel_count=2.5), make_raw(per_sentinel_count=9.0)]
    results = validate_records(records, session)
    assert all(r.validation_status == "flagged" for r in results)
    assert all("conflicting_duplicate_extraction" in r.flag_reason for r in results)


def test_all_extract_parsers_run_against_fixtures():
    sources = {
        "神奈川県": "kanagawa_sample.csv",
        "千葉市": "chiba_city_sample.csv",
        "北九州市": "kitakyushu_sample.csv",
        "京都府": "kyoto_sample.csv",
        "沖縄県": "okinawa_sample.xlsx",
        "山梨県": "yamanashi_sample.csv",
    }
    for prefecture, filename in sources.items():
        raw_bytes = (FIXTURES_DIR / filename).read_bytes()
        records = PARSERS[prefecture](raw_bytes, source_url="test")
        assert len(records) > 0
        assert all(r.prefecture == prefecture for r in records)


def test_extract_then_validate_end_to_end_passes():
    session = make_session()
    raw_bytes = (FIXTURES_DIR / "kanagawa_sample.csv").read_bytes()
    raw_records = PARSERS["神奈川県"](raw_bytes, source_url="test")
    validated = validate_records(raw_records, session)
    assert len(validated) == len(raw_records)
    assert all(v.validation_status == "passed" for v in validated)
