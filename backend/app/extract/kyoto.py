"""京都府: 京都府感染症情報センターが週ごとに配布する「発生地図」用CSV
(直接パース, spec 3.2)。

当初のPoC想定(疾患×保健所の素のHTML表)は、実際にページを開いて確認した
ところ、地図ページ(map.html)には現在選択中の1疾患・12地域分の小さなHTML表
しか無く、全疾患をまとめて機械的に取得するには同ページからリンクされている
CSV(Shift_JIS)の方が適していた。そちらを直接パース対象とする。

CSVの構造(ヘッダ3行):
    1行目: "<年>年<週>週　定点報告（週）発生地図（京都府全域）,報告数,...,定点あたり,...,警報・注意報,..."
    2行目: 地域グループ見出し(京都市 / 京都市以外)
    3行目: 疾患名,<地域1>,<地域2>,...,<地域12>,<地域1>,...(定点あたりブロック),...(警報・注意報ブロック)
    4行目以降: <疾患名>,<報告数×12>,<定点あたり×12>,<警報記号×12>

京都市内は行政区ではなく保健所管区(5区分: 北・左京/上京・中京・下京/
東山・山科/南・伏見/右京・西京)単位。京都市以外は7保健所。
"""

import csv
import io
import re

from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "京都府"

_REGIONS = [
    "北・左京", "上京・中京・下京", "東山・山科", "南・伏見", "右京・西京",
    "乙訓", "山城北", "山城南", "南丹", "中丹西", "中丹東", "丹後",
]
_N_REGIONS = len(_REGIONS)

_TITLE_RE = re.compile(r"(\d{4})年(\d+)週")


def _parse_value(raw: str) -> float | None:
    raw = raw.strip()
    if raw in ("", "-", "…"):
        return None
    return float(raw)


def parse(raw_bytes: bytes, source_url: str | None = None) -> list[RawRecord]:
    text = raw_bytes.decode("shift_jis")
    rows = list(csv.reader(io.StringIO(text)))

    match = _TITLE_RE.search(rows[0][0])
    year, week = int(match.group(1)), int(match.group(2))

    records = []
    for row in rows[3:]:
        if not row or not row[0].strip():
            continue
        disease = row[0].strip()
        patient_counts = row[1 : 1 + _N_REGIONS]
        sentinel_counts = row[1 + _N_REGIONS : 1 + 2 * _N_REGIONS]

        for region, patient_raw, sentinel_raw in zip(_REGIONS, patient_counts, sentinel_counts):
            patient = _parse_value(patient_raw)
            records.append(
                RawRecord(
                    year=year,
                    week_number=week,
                    week_start_date=week_start_date(year, week),
                    prefecture=PREFECTURE,
                    region=region,
                    disease=disease,
                    patient_count=int(patient) if patient is not None else None,
                    per_sentinel_count=_parse_value(sentinel_raw),
                    source_tier="direct_parse",
                    source_url=source_url,
                    extracted_by="pandas",
                )
            )
    return records
