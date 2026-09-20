"""神奈川県: 感染症情報センターが疾患ごと・年ごとに配布するCSV (直接パース, spec 3.2)。

実データの構造は当初のPoC想定(年,週,保健所名,疾患名,患者数,定点当たり報告数の
単純な列)とは異なり、以下のような「疾患1件・週が列」のワイド形式だった:

    <疾患名>,定点当たり報告数、神奈川県
    <作成日>
    ,第1週,第2週,...,第N週
    <地域名>,<値>,<値>,...

疾患名はファイル1つにつき1つ(ファイル名 `<年>_<疾患>.csv` にも年が入っている)。
患者数(実数)はこのCSVには含まれないため patient_count は常に None。
値の "-" は報告0件(0として扱う。spec 5.2的にも0は有効な観測値)、
"…" は未集計(Noneとして扱う)。
"""

import csv
import io
import re
from urllib.parse import urlparse

from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "神奈川県"

# ファイル名(URLパスの末尾)が `<年>_<疾患>.csv` 形式であることを前提にする。
# URLパスの途中に別の4桁ディレクトリ名(例: 0001_weekly)が含まれる場合があるため、
# ファイル名部分だけを対象に年を抽出する(spec: 推測で丸めず、取れなければ作成日から補う)。
_YEAR_IN_FILENAME_RE = re.compile(r"^(\d{4})_")
_YEAR_IN_CREATED_RE = re.compile(r"(\d{4})年")
_WEEK_HEADER_RE = re.compile(r"第(\d+)週")


def _parse_value(raw: str) -> float | None:
    raw = raw.strip()
    if raw == "-":
        return 0.0
    if raw == "" or raw == "…":
        return None
    return float(raw)


def parse(raw_bytes: bytes, source_url: str | None = None) -> list[RawRecord]:
    text = raw_bytes.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))

    disease = rows[0][0].strip()

    filename = urlparse(source_url or "").path.rsplit("/", 1)[-1]
    year_match = _YEAR_IN_FILENAME_RE.search(filename)
    if year_match is None:
        year_match = _YEAR_IN_CREATED_RE.search(rows[1][0])
    year = int(year_match.group(1))

    header = rows[2]
    week_numbers = [int(m.group(1)) if (m := _WEEK_HEADER_RE.search(cell)) else None for cell in header]

    records = []
    for row in rows[3:]:
        if not row or not row[0].strip():
            continue
        region = row[0].strip()
        for col_index, cell in enumerate(row[1:], start=1):
            if col_index >= len(week_numbers) or week_numbers[col_index] is None:
                continue
            week = week_numbers[col_index]
            per_sentinel = _parse_value(cell)
            records.append(
                RawRecord(
                    year=year,
                    week_number=week,
                    week_start_date=week_start_date(year, week),
                    prefecture=PREFECTURE,
                    region=region,
                    disease=disease,
                    patient_count=None,
                    per_sentinel_count=per_sentinel,
                    source_tier="direct_parse",
                    source_url=source_url,
                    extracted_by="pandas",
                )
            )
    return records
