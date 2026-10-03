"""福井県: 感染症情報センターが保健所×年×指標(定点あたり/報告実数)ごとに
個別配布するCSV (直接パース, spec 3.2)。

実データの構造は以下の通り(全16ファイルで共通、実際のダウンロード結果で確認済み):

    (空行)
    "","令和<N>年","","定点把握・週報・","","（報告実数）or（定点当たり報告数）","","集計表","","","<地域名>",
    (空行)
    "","（単位：...）",
    "","週","期間",<23疾病名>,
    "","<週番号>","<和暦の期間文字列>",<23個の値>,
    ...
    (空行)

1ファイルには「報告実数」と「定点当たり報告数」のどちらか一方しか入っていない
ため、同一保健所・同一年の2ファイル(実数用+定点あたり用)を対にして読み、
(週,疾病)単位でマージしてから1レコードにする。バラバラのまま2レコードとして
Validation層に渡すと、per_sentinel_countの値が一方Noneでもう一方に実数が
入っている状態を「同一ソース内で抽出結果が割れた」(spec 5.3)と誤検出して
しまうため。

年は各ファイル冒頭の和暦表記(例:"令和８年")から算出する(令和1年=2019年)。
地域名(全県/福井市/福井/坂井/二州/若狭/奥越/丹南)も同じ行の末尾セルから
そのまま取得し、コード表からの推測はしない(spec 5.1: 推測で丸めない)。
値が空文字の場合は0件(None ではなく0)として扱う。
"""

import csv
import io
import re
import unicodedata

from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "福井県"

_ERA_RE = re.compile(r"令和(\d+)年")
_HEADER_PREFIX_LEN = 3  # 先頭空列 + 週 + 期間


def _reiwa_to_gregorian(cell: str) -> int:
    normalized = unicodedata.normalize("NFKC", cell)
    match = _ERA_RE.search(normalized)
    return int(match.group(1)) + 2018


def _parse_value(raw: str) -> float | None:
    raw = raw.strip()
    if raw == "":
        return 0.0
    return float(raw)


class _ParsedFile:
    def __init__(self, region: str, year: int, diseases: list[str], rows: dict[int, list[str]]):
        self.region = region
        self.year = year
        self.diseases = diseases
        self.rows = rows  # week_number -> 23個の生の値(文字列)


def _parse_file(raw_bytes: bytes) -> _ParsedFile:
    text = raw_bytes.decode("cp932")
    all_rows = list(csv.reader(io.StringIO(text)))
    non_empty = [r for r in all_rows if any(c.strip() for c in r)]

    title_row = non_empty[0]
    year = _reiwa_to_gregorian(title_row[1])
    region = next(c.strip() for c in reversed(title_row) if c.strip())

    header_row = next(r for r in non_empty if r[1].strip() == "週")
    diseases = [c.strip() for c in header_row[_HEADER_PREFIX_LEN:] if c.strip()]

    rows: dict[int, list[str]] = {}
    header_index = non_empty.index(header_row)
    for row in non_empty[header_index + 1 :]:
        week = int(row[1])
        rows[week] = row[_HEADER_PREFIX_LEN : _HEADER_PREFIX_LEN + len(diseases)]

    return _ParsedFile(region=region, year=year, diseases=diseases, rows=rows)


def parse_pair(
    report_bytes: bytes,
    sentinel_bytes: bytes,
    report_source_url: str | None = None,
    sentinel_source_url: str | None = None,
) -> list[RawRecord]:
    """報告実数CSVと定点当たり報告数CSV(同一保健所・同一年)を対で読み、マージする。"""
    report = _parse_file(report_bytes)
    sentinel = _parse_file(sentinel_bytes)

    records = []
    weeks = set(report.rows) | set(sentinel.rows)
    for week in weeks:
        report_values = report.rows.get(week)
        sentinel_values = sentinel.rows.get(week)
        for i, disease in enumerate(report.diseases):
            patient = _parse_value(report_values[i]) if report_values else None
            sentinel_value = _parse_value(sentinel_values[i]) if sentinel_values else None
            records.append(
                RawRecord(
                    year=report.year,
                    week_number=week,
                    week_start_date=week_start_date(report.year, week),
                    prefecture=PREFECTURE,
                    region=report.region,
                    disease=disease,
                    patient_count=int(patient) if patient is not None else None,
                    per_sentinel_count=sentinel_value,
                    source_tier="direct_parse",
                    source_url=report_source_url or sentinel_source_url,
                    extracted_by="pandas",
                )
            )
    return records
