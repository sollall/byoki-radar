"""沖縄県: 保健所別・年齢別内訳付きExcel配布 (直接パース, spec 3.2)。

共通スキーマは年齢区分を持たないため、年齢区分="計"(合計)行のみを採用する。

想定列: 年,週,保健所,疾患名,年齢区分,患者数,定点当たり報告数
"""

import io

import pandas as pd

from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "沖縄県"
TOTAL_AGE_LABEL = "計"


def parse(raw_bytes: bytes, source_url: str | None = None) -> list[RawRecord]:
    df = pd.read_excel(io.BytesIO(raw_bytes))
    df = df[df["年齢区分"] == TOTAL_AGE_LABEL]
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
                region=str(row["保健所"]).strip(),
                disease=str(row["疾患名"]).strip(),
                patient_count=int(row["患者数"]) if pd.notna(row["患者数"]) else None,
                per_sentinel_count=float(row["定点当たり報告数"]) if pd.notna(row["定点当たり報告数"]) else None,
                source_tier="direct_parse",
                source_url=source_url,
                extracted_by="pandas",
            )
        )
    return records
