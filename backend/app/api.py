"""Map層向けAPI (spec section 7)。
Store層(DB)を直接参照せず、フロントはこのAPIのみを参照する。
ビジネスロジックは最小限(クエリのラップ+粒度/色スケール情報の付与)に留める。
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .db import InfectiousDiseaseReport, get_session, init_db
from .masters import ALL_REGION, DISEASES

app = FastAPI(title="byoki-radar API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/diseases")
def list_diseases():
    return [{"code": code, **meta} for code, meta in DISEASES.items()]


@app.get("/api/weeks")
def list_weeks():
    session = get_session()
    rows = session.execute(
        select(InfectiousDiseaseReport.year, InfectiousDiseaseReport.week_number)
        .where(InfectiousDiseaseReport.validation_status == "passed")
        .distinct()
        .order_by(InfectiousDiseaseReport.year, InfectiousDiseaseReport.week_number)
    ).all()
    session.close()
    return [{"year": y, "week_number": w} for y, w in rows]


@app.get("/api/reports")
def get_reports(
    disease: str = Query(...),
    year: int = Query(...),
    week_number: int = Query(...),
):
    """指定した疾患・週の全自治体の値を返す。
    色スケールの疾患別正規化 (spec 7.2): この疾患・この週のデータのmin/maxを
    scale_min/scale_max として都度計算し、フロントの固定スケール化を防ぐ。
    全地域が0の場合は no_data=true とし、フロントで「報告なし」パターン表示に使う。
    """
    if disease not in DISEASES:
        raise HTTPException(status_code=404, detail=f"unknown disease code: {disease}")

    report_type = DISEASES[disease]["report_type"]
    value_field = (
        InfectiousDiseaseReport.patient_count
        if report_type == "case_based"
        else InfectiousDiseaseReport.per_sentinel_count
    )

    session = get_session()
    rows = session.execute(
        select(
            InfectiousDiseaseReport.prefecture,
            InfectiousDiseaseReport.region,
            InfectiousDiseaseReport.patient_count,
            InfectiousDiseaseReport.per_sentinel_count,
        ).where(
            InfectiousDiseaseReport.disease == disease,
            InfectiousDiseaseReport.year == year,
            InfectiousDiseaseReport.week_number == week_number,
            InfectiousDiseaseReport.validation_status == "passed",
        )
    ).all()
    session.close()

    granularity_by_prefecture: dict[str, str] = {}
    values = []
    items = []
    for prefecture, region, patient_count, per_sentinel_count in rows:
        value = patient_count if report_type == "case_based" else per_sentinel_count
        items.append(
            {
                "prefecture": prefecture,
                "region": region,
                "patient_count": patient_count,
                "per_sentinel_count": per_sentinel_count,
                "value": value,
            }
        )
        if value is not None:
            values.append(value)
        current = granularity_by_prefecture.get(prefecture, "prefecture")
        if region != ALL_REGION:
            current = "region"
        granularity_by_prefecture[prefecture] = current

    no_data = len(values) > 0 and max(values) == 0
    scale_min = min(values) if values else None
    scale_max = max(values) if values else None

    return {
        "disease": disease,
        "report_type": report_type,
        "year": year,
        "week_number": week_number,
        "scale_min": scale_min,
        "scale_max": scale_max,
        "no_data": no_data,
        "available_granularity": granularity_by_prefecture,
        "items": items,
    }
