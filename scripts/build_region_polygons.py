"""frontend/region_polygons/*.geojson を生成するスクリプト。

保健所管区(乙訓・山城北...等)の境界線を配布している統一データセットは無いため、
市区町村ポリゴンを「どの市町村がどの保健所管区に属するか」の対応表に従って
結合(dissolve)して作る。

## 依存データ
市区町村ポリゴンは npm パッケージ `japan-choropleth`
(https://github.com/kyodo-official/japan-choropleth) を使う。このパッケージの
ポリゴンデータは国土交通省 国土数値情報「行政区域データ 2025年版」(CC-BY 4.0)を
加工したもの。二次利用にあたっては原著者のクレジット表示が必要
(このスクリプト・README・frontend側での表示のいずれかにクレジットを残すこと)。

```bash
npm pack japan-choropleth@0.1.0
tar xzf japan-choropleth-0.1.0.tgz \
  package/data/geojson/by-prefecture/<都道府県コード2桁>/municipalities.geojson
```

## 対応表の出典
- 京都府: 厚生労働省「保健所管轄区域案内」(https://www.mhlw.go.jp/bunya/kenkou/hokenjo/h_26.html)
  および京都府公式サイトの記載を確認。京都市内の5区分(北・左京、上京・中京・下京、
  東山・山科、南・伏見、右京・西京)は、backend/app/extract/kyoto.py が実際に取得した
  京都府発生地図CSVのヘッダー表記そのもの(推測ではなく確認済みの実データ表記)。

対応表は spec 5.1 の方針(推測で丸めない)に従い、出典を確認できたものだけを
記載する。未確認の県は追加しない。

## 実行方法
```bash
pip install shapely
python3 scripts/build_region_polygons.py <municipalities.geojsonのパス> <出力先.geojson> <対象都道府県名>
```
"""

import json
import sys

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

# 京都市内: 区(ward)の組み合わせ。backend/app/extract/kyoto.py の _REGIONS と対応。
KYOTO_CITY_WARD_GROUPS = {
    "北・左京": ["北区", "左京区"],
    "上京・中京・下京": ["上京区", "中京区", "下京区"],
    "東山・山科": ["東山区", "山科区"],
    "南・伏見": ["南区", "伏見区"],
    "右京・西京": ["右京区", "西京区"],
}

# 京都市以外: 厚生労働省「保健所管轄区域案内」で確認した市町村対応。
KYOTO_HEALTH_CENTER_MUNICIPALITY_GROUPS = {
    "乙訓": ["向日市", "長岡京市", "大山崎町"],
    "山城北": ["宇治市", "城陽市", "八幡市", "京田辺市", "久御山町", "井手町", "宇治田原町"],
    "山城南": ["木津川市", "笠置町", "和束町", "精華町", "南山城村"],
    "南丹": ["亀岡市", "南丹市", "京丹波町"],
    "中丹西": ["福知山市"],
    "中丹東": ["舞鶴市", "綾部市"],
    "丹後": ["宮津市", "京丹後市", "伊根町", "与謝野町"],
}

REGION_GROUPS_BY_PREFECTURE = {
    "京都府": {
        "city_name": "京都市",
        "ward_groups": KYOTO_CITY_WARD_GROUPS,
        "municipality_groups": KYOTO_HEALTH_CENTER_MUNICIPALITY_GROUPS,
    },
}


def build(municipalities_path: str, prefecture: str) -> dict:
    config = REGION_GROUPS_BY_PREFECTURE[prefecture]
    data = json.load(open(municipalities_path, encoding="utf-8"))

    by_ward, by_municipality = {}, {}
    for f in data["features"]:
        props = f["properties"]
        geom = shape(f["geometry"])
        if props["municipality"] == config["city_name"]:
            by_ward[props["ward"]] = geom
        else:
            by_municipality[props["municipality"]] = geom

    features = []
    for region, wards in config["ward_groups"].items():
        geoms = [by_ward[w] for w in wards if w in by_ward]
        if len(geoms) != len(wards):
            missing = set(wards) - set(by_ward)
            raise ValueError(f"{region}: 区が見つからない {missing}")
        merged = unary_union(geoms)
        features.append(
            {
                "type": "Feature",
                "properties": {"region": region, "prefecture": prefecture},
                "geometry": mapping(merged),
            }
        )

    for region, munis in config["municipality_groups"].items():
        geoms = [by_municipality[m] for m in munis if m in by_municipality]
        if len(geoms) != len(munis):
            missing = set(munis) - set(by_municipality)
            raise ValueError(f"{region}: 市町村が見つからない {missing}")
        merged = unary_union(geoms)
        features.append(
            {
                "type": "Feature",
                "properties": {"region": region, "prefecture": prefecture},
                "geometry": mapping(merged),
            }
        )

    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    municipalities_path, out_path, prefecture = sys.argv[1:4]
    result = build(municipalities_path, prefecture)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False)
    print(f"{len(result['features'])} regions -> {out_path}")
