"""Validation層 (spec section 5). Extract層の出力(RawRecord)を検証し、
ValidatedRecordに変換する。抽出手段(pandas/llm)によらず同じルールを適用する。
"""

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import InfectiousDiseaseReport
from .masters import DISEASES, PER_SENTINEL_MAX, REGION_MASTERS, WEEK_OVER_WEEK_FLAG_RATIO
from .schemas import RawRecord, ValidatedRecord

# 自治体表記のゆれ -> 内部enumコードへのマッピング。
# 未知の表記は正規化できないため、そのまま(コード化されずに)flaggedとなる。
_DISEASE_LABEL_TO_CODE = {v["label"]: k for k, v in DISEASES.items()}


def _normalize_disease(raw_label: str) -> tuple[str, bool]:
    """(コードまたは元の表記, 既知disease かどうか) を返す。丸めは行わない。"""
    code = _DISEASE_LABEL_TO_CODE.get(raw_label.strip())
    if code is not None:
        return code, True
    return raw_label, False


def _previous_week_value(
    session: Session, prefecture: str, region: str, disease_code: str, year: int, week_number: int
) -> float | None:
    prev_week = week_number - 1
    prev_year = year
    if prev_week < 1:
        prev_week = 52
        prev_year = year - 1
    row = session.execute(
        select(InfectiousDiseaseReport.per_sentinel_count).where(
            InfectiousDiseaseReport.prefecture == prefecture,
            InfectiousDiseaseReport.region == region,
            InfectiousDiseaseReport.disease == disease_code,
            InfectiousDiseaseReport.year == prev_year,
            InfectiousDiseaseReport.week_number == prev_week,
            InfectiousDiseaseReport.validation_status == "passed",
        )
    ).first()
    return row[0] if row and row[0] is not None else None


def validate_record(raw: RawRecord, session: Session | None = None) -> ValidatedRecord:
    reasons: list[str] = []

    disease_code, disease_known = _normalize_disease(raw.disease)
    if not disease_known:
        reasons.append(f"unknown_disease:{raw.disease}")

    region_master = REGION_MASTERS.get(raw.prefecture)
    if region_master is None:
        reasons.append(f"unknown_prefecture:{raw.prefecture}")
    elif raw.region not in region_master:
        reasons.append(f"unknown_region:{raw.region}")

    if raw.per_sentinel_count is not None:
        if raw.per_sentinel_count < 0 or raw.per_sentinel_count > PER_SENTINEL_MAX:
            reasons.append("per_sentinel_count_out_of_range")

    if session is not None and disease_known and raw.per_sentinel_count is not None:
        prev = _previous_week_value(
            session, raw.prefecture, raw.region, disease_code, raw.year, raw.week_number
        )
        if prev is not None and prev > 0 and raw.per_sentinel_count >= prev * WEEK_OVER_WEEK_FLAG_RATIO:
            reasons.append("week_over_week_spike")

    # patient_count / per_sentinel_count の整合性チェックは、保健所別の定点数
    # マスタが未整備のため、PoC段階では実施しない (spec 5.2 は将来拡張として残す)。

    status = "flagged" if reasons else "passed"
    return ValidatedRecord(
        **{**raw.model_dump(), "disease": disease_code if disease_known else raw.disease},
        validation_status=status,
        flag_reason=";".join(reasons) or None,
        fetched_at=datetime.utcnow(),
    )


def validate_records(raws: Iterable[RawRecord], session: Session) -> list[ValidatedRecord]:
    """複数レコードをまとめて検証する。同一ソース内で複数回抽出した結果が割れる
    場合の検出(spec 5.3)のため、(prefecture,region,disease,week)単位でグルーピングする。
    """
    grouped: dict[tuple, list[RawRecord]] = defaultdict(list)
    for r in raws:
        grouped[(r.prefecture, r.region, r.disease, r.year, r.week_number)].append(r)

    out: list[ValidatedRecord] = []
    for key, group in grouped.items():
        if len(group) > 1:
            values = {g.per_sentinel_count for g in group}
            if len(values) > 1:
                for g in group:
                    v = validate_record(g, session)
                    v.validation_status = "flagged"
                    v.flag_reason = ";".join(filter(None, [v.flag_reason, "conflicting_duplicate_extraction"]))
                    out.append(v)
                continue
        for g in group:
            out.append(validate_record(g, session))
    return out
