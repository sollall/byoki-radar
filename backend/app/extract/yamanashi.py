"""山梨県: やまなしデータプラットフォーム(CKANオープンデータカタログ)経由のCSV配布
(直接パース, spec 3.2)。県全体集計のみで保健所別内訳は無いため region は常に ALL。

実データのCSVはワイド形式: 疾患名ごとに `{疾患名}_累積`(その週の患者数実数。
列名に反し累計ではなく週別値) / `{疾患名}_定当`(定点当たり報告数) /
`{疾患名}_推移`(トレンド文, 未使用) / `{疾患名}_状況`(警報レベル文, 未使用) の
4列一組が並ぶ。年週は `期間` 列 (例:"2026年01週(12月29日～01月04日)") から抽出する。
"""

import io
import re

import pandas as pd

from ..masters import ALL_REGION
from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "山梨県"

_PERIOD_RE = re.compile(r"(\d{4})年(\d{2})週")


def _parse_value(raw: str) -> float | None:
    if raw is None or str(raw).strip() in ("", "-"):
        return None
    return float(raw)


def parse(raw_bytes: bytes, source_url: str | None = None) -> list[RawRecord]:
    df = pd.read_csv(io.BytesIO(raw_bytes), encoding="utf-8-sig")

    diseases = [col[: -len("_累積")] for col in df.columns if col.endswith("_累積")]

    records = []
    for _, row in df.iterrows():
        match = _PERIOD_RE.search(str(row["期間"]))
        year, week = int(match.group(1)), int(match.group(2))

        for disease in diseases:
            patient_raw = _parse_value(row[f"{disease}_累積"])
            sentinel_raw = _parse_value(row[f"{disease}_定当"])
            records.append(
                RawRecord(
                    year=year,
                    week_number=week,
                    week_start_date=week_start_date(year, week),
                    prefecture=PREFECTURE,
                    region=ALL_REGION,
                    disease=disease,
                    patient_count=int(patient_raw) if patient_raw is not None else None,
                    per_sentinel_count=sentinel_raw,
                    source_tier="direct_parse",
                    source_url=source_url,
                    extracted_by="pandas",
                )
            )
    return records
