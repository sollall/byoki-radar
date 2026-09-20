"""Raw層(fixtures/) -> Extract層 -> Validation層 -> Store層(DB) を一通り実行する。

`python -m app.seed` で実行する。実運用ではRaw層取得(定期クロール)と
このロード処理は別ジョブ(Dagster asset chain, spec section 8)になるが、
PoC/MVPでは同一スクリプトにまとめている。
"""

from pathlib import Path

from .db import InfectiousDiseaseReport, init_db, get_session
from .extract import PARSERS
from .validation import validate_records

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

SOURCES = {
    # 神奈川県・京都府・山梨県は、他と異なり実際にダウンロードした本物のオープンデータ。
    "神奈川県": FIXTURES_DIR / "kanagawa_sample.csv",
    "千葉市": FIXTURES_DIR / "chiba_city_sample.csv",
    "北九州市": FIXTURES_DIR / "kitakyushu_sample.csv",
    "京都府": FIXTURES_DIR / "kyoto_sample.csv",
    "沖縄県": FIXTURES_DIR / "okinawa_sample.xlsx",
    "山梨県": FIXTURES_DIR / "yamanashi_sample.csv",
}

_REAL_DATA_SOURCE_URLS = {
    "山梨県": "https://catalog.dataplatform-yamanashi.jp/dataset/a7f43811-ef7d-49c6-9182-fa7bfabdfbf5/resource/674e45f2-145c-430d-af18-d228c7e0510c/download/11595_survey_yamanashi_week.csv",
    "神奈川県": "https://www.pref.kanagawa.jp/sys/eiken/003_center/0001_weekly/csv/2026_influenza.csv",
    "京都府": "https://www.pref.kyoto.jp/idsc/data/week/area-map/2026/documents/202637_2-2-5.csv",
}


def run(reset: bool = True) -> dict:
    init_db()
    session = get_session()
    if reset:
        session.query(InfectiousDiseaseReport).delete()
        session.commit()

    summary = {"passed": 0, "flagged": 0}
    for prefecture, path in SOURCES.items():
        parser = PARSERS[prefecture]
        raw_bytes = path.read_bytes()
        source_url = _REAL_DATA_SOURCE_URLS.get(prefecture, f"local-fixture://{path.name}")
        raw_records = parser(raw_bytes, source_url=source_url)
        validated = validate_records(raw_records, session)
        for v in validated:
            session.add(
                InfectiousDiseaseReport(
                    year=v.year,
                    week_number=v.week_number,
                    week_start_date=v.week_start_date,
                    prefecture=v.prefecture,
                    region=v.region,
                    disease=v.disease,
                    patient_count=v.patient_count,
                    per_sentinel_count=v.per_sentinel_count,
                    source_tier=v.source_tier,
                    source_url=v.source_url,
                    extracted_by=v.extracted_by,
                    fetched_at=v.fetched_at,
                    validation_status=v.validation_status,
                    flag_reason=v.flag_reason,
                )
            )
            summary[v.validation_status] += 1
        session.commit()
    session.close()
    return summary


if __name__ == "__main__":
    result = run()
    print(f"passed={result['passed']} flagged={result['flagged']}")
