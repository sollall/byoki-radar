"""神奈川県: 保健所管区別・週次CSV配布 (直接パース, spec 3.2)。

想定列: 年,週,保健所名,疾患名,患者数,定点当たり報告数
"""

import io

import pandas as pd

from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "神奈川県"


def parse(raw_bytes: bytes, source_url: str | None = None) -> list[RawRecord]:
    df = pd.read_csv(io.BytesIO(raw_bytes), encoding="utf-8")
    records = []
    for _, row in df.iterrows():
        year = int(row["年"])
        week = int(row["週"])
        records.append(
            RawRecord(
                year=year,
                week_number=week,
                week_start_date=week_start_date(year, week),
                prefecture=PREFECTURE,
                region=str(row["保健所名"]).strip(),
                disease=str(row["疾患名"]).strip(),
                patient_count=int(row["患者数"]) if pd.notna(row["患者数"]) else None,
                per_sentinel_count=float(row["定点当たり報告数"]) if pd.notna(row["定点当たり報告数"]) else None,
                source_tier="direct_parse",
                source_url=source_url,
                extracted_by="pandas",
            )
        )
    return records
