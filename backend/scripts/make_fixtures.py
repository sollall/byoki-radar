"""PoC用のサンプル生データ(Raw層相当)を fixtures/ に生成するスクリプト。

注意: ここで生成する数値は実際の感染症発生動向データではなく、
パイプライン(Extract->Validation->Store->Map)の動作確認用に作った
架空のサンプルデータである。
"""

import random
from pathlib import Path

import pandas as pd

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)

random.seed(42)

DISEASES = ["インフルエンザ", "COVID-19", "感染性胃腸炎", "手足口病", "RSウイルス感染症"]
YEAR = 2025
WEEKS = [18, 19, 20]

KANAGAWA_REGIONS = ["横須賀三崎", "鎌倉", "藤沢", "厚木", "横浜市", "川崎市"]
KYOTO_REGIONS = ["乙訓", "山城北", "山城南", "南丹", "中丹西", "中丹東", "丹後", "京都市"]
OKINAWA_REGIONS = ["那覇", "中部", "北部", "宮古", "八重山", "南部"]


def sample_value(disease: str) -> float:
    if disease == "RSウイルス感染症":
        return 0.0  # 「報告なし」パターン確認用に常に0
    base = {"インフルエンザ": 3, "COVID-19": 5, "感染性胃腸炎": 15, "手足口病": 1, "水痘": 1}.get(disease, 3)
    return round(max(0.0, random.gauss(base, base * 0.4)), 2)


def make_kanagawa():
    rows = []
    for week in WEEKS:
        for region in KANAGAWA_REGIONS:
            for disease in DISEASES:
                per_sentinel = sample_value(disease)
                rows.append(
                    {
                        "年": YEAR,
                        "週": week,
                        "保健所名": region,
                        "疾患名": disease,
                        "患者数": int(per_sentinel * 6),
                        "定点当たり報告数": per_sentinel,
                    }
                )
    pd.DataFrame(rows).to_csv(FIXTURES_DIR / "kanagawa_sample.csv", index=False, encoding="utf-8")


def make_city_csv(prefecture_label: str, filename: str):
    rows = []
    for week in WEEKS:
        for disease in DISEASES:
            per_sentinel = sample_value(disease)
            rows.append(
                {
                    "年": YEAR,
                    "週": week,
                    "疾患名": disease,
                    "患者数": int(per_sentinel * 20),
                    "定点当たり報告数": per_sentinel,
                }
            )
    pd.DataFrame(rows).to_csv(FIXTURES_DIR / filename, index=False, encoding="utf-8")


def make_kyoto():
    week = WEEKS[-1]
    thead = "".join(f"<th>{h}</th>" for h in ["保健所", "疾患名", "患者数", "定点当たり報告数"])
    body_rows = []
    for region in KYOTO_REGIONS:
        for disease in DISEASES:
            per_sentinel = sample_value(disease)
            body_rows.append(
                "<tr>"
                f"<td>{region}</td><td>{disease}</td>"
                f"<td>{int(per_sentinel * 5)}</td><td>{per_sentinel}</td>"
                "</tr>"
            )
    html = (
        f'<table data-year="{YEAR}" data-week="{week}">'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    (FIXTURES_DIR / "kyoto_sample.html").write_text(html, encoding="utf-8")


def make_okinawa():
    rows = []
    for week in WEEKS:
        for region in OKINAWA_REGIONS:
            for disease in DISEASES:
                per_sentinel = sample_value(disease)
                for age in ["0-4歳", "5-14歳", "15歳以上", "計"]:
                    if age == "計":
                        patient = int(per_sentinel * 4)
                        sentinel_value = per_sentinel
                    else:
                        patient = random.randint(0, 3)
                        sentinel_value = None
                    rows.append(
                        {
                            "年": YEAR,
                            "週": week,
                            "保健所": region,
                            "疾患名": disease,
                            "年齢区分": age,
                            "患者数": patient,
                            "定点当たり報告数": sentinel_value,
                        }
                    )
    pd.DataFrame(rows).to_excel(FIXTURES_DIR / "okinawa_sample.xlsx", index=False)


if __name__ == "__main__":
    make_kanagawa()
    make_city_csv("千葉市", "chiba_city_sample.csv")
    make_city_csv("北九州市", "kitakyushu_sample.csv")
    make_kyoto()
    make_okinawa()
    print("fixtures written to", FIXTURES_DIR)
