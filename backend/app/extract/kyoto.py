"""京都府: 保健所別の素のHTML表配布 (直接パース, spec 3.2)。

想定HTML構造: <table data-year="2024" data-week="20"> に
保健所/疾患名/患者数/定点当たり報告数 の列を持つ行が並ぶ。
実際のページ構造に合わせて data-year/data-week の取得元は要調整。
"""

from bs4 import BeautifulSoup

from ..schemas import RawRecord
from .common import week_start_date

PREFECTURE = "京都府"


def parse(raw_bytes: bytes, source_url: str | None = None) -> list[RawRecord]:
    soup = BeautifulSoup(raw_bytes, "lxml")
    table = soup.find("table")
    year = int(table["data-year"])
    week = int(table["data-week"])

    header_cells = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]
    col_index = {name: i for i, name in enumerate(header_cells)}

    records = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        patient_raw = cells[col_index["患者数"]]
        sentinel_raw = cells[col_index["定点当たり報告数"]]
        records.append(
            RawRecord(
                year=year,
                week_number=week,
                week_start_date=week_start_date(year, week),
                prefecture=PREFECTURE,
                region=cells[col_index["保健所"]],
                disease=cells[col_index["疾患名"]],
                patient_count=int(patient_raw) if patient_raw not in ("", "-") else None,
                per_sentinel_count=float(sentinel_raw) if sentinel_raw not in ("", "-") else None,
                source_tier="direct_parse",
                source_url=source_url,
                extracted_by="pandas",
            )
        )
    return records
