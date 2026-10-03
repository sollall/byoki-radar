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
- 神奈川県: 神奈川県公式サイト「保健福祉事務所一覧」の記載を確認。実データCSVの地域名
  (例:"平塚"と"平塚　秦野センター"が別行)と、各保健福祉事務所/センターの管轄市町村を
  対応付けた。"全県"(県全体集計)と"県域"(保健所設置市を除く県全体)は他地域の合算に
  なるため、ポリゴンとしては生成しない(他地域と重複表示になるため)。
  市区町村ポリゴン側は表記が「茅ヶ崎市」(小さいヶ)だが、実データCSVは「茅ケ崎市」
  (大きいケ)という表記ゆれがあり、出力region名は実データ側の表記に合わせる。
- 福井県: 福井県公式サイトの「県健康福祉センター（県保健所）管轄市町一覧」を確認。
  ただし若狭町は同一市町内で管轄が分かれる(「旧三方町部分」は二州、「旧上中町部分」は
  若狭)ため、現在の市町村単位ポリゴンでは正確に分割できない。暫定的に若狭町全体を
  「若狭」に割り当てている(既知の簡略化であり、実データのvalidation側には影響しない)。
- 沖縄県: 沖縄県公式サイトの保健所管轄区域案内を確認。

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

# 神奈川県: 神奈川県「保健福祉事務所一覧」で確認。横浜市・川崎市・相模原市・横須賀市・
# 藤沢市は政令指定都市/中核市等で独自に保健所を設置しており、市域=管轄区域。
# 茅ケ崎市保健所は寒川町も管轄する。
KANAGAWA_MUNICIPALITY_GROUPS = {
    "横浜市": ["横浜市"],
    "川崎市": ["川崎市"],
    "相模原市": ["相模原市"],
    "横須賀市": ["横須賀市"],
    "藤沢市": ["藤沢市"],
    "茅ケ崎市": ["茅ヶ崎市", "寒川町"],
    "平塚": ["平塚市", "大磯町", "二宮町"],
    "平塚　秦野センター": ["秦野市", "伊勢原市"],
    "鎌倉": ["鎌倉市", "逗子市", "葉山町"],
    "鎌倉　三崎センター": ["三浦市"],
    "小田原": ["小田原市", "箱根町", "真鶴町", "湯河原町"],
    "小田原　足柄上センター": ["南足柄市", "中井町", "大井町", "松田町", "山北町", "開成町"],
    "厚木": ["厚木市", "海老名市", "座間市", "愛川町", "清川村"],
    "厚木　大和センター": ["大和市", "綾瀬市"],
}

# 福井県: 福井県公式サイト「県健康福祉センター（県保健所）管轄市町一覧」で確認。
# 若狭町は市町合併前の旧三方町部分が二州、旧上中町部分が若狭の管轄だが、現在の
# 市町村単位ポリゴンでは分割できないため全体を若狭に割り当てる(上記docstring参照)。
FUKUI_MUNICIPALITY_GROUPS = {
    "福井市": ["福井市"],
    "福井": ["永平寺町"],
    "坂井": ["あわら市", "坂井市"],
    "奥越": ["大野市", "勝山市"],
    "丹南": ["鯖江市", "越前町", "越前市", "池田町", "南越前町"],
    "二州": ["敦賀市", "美浜町"],
    "若狭": ["小浜市", "高浜町", "おおい町", "若狭町"],
}

# 沖縄県: 沖縄県公式サイトの保健所管轄区域案内で確認。「所属未定地」は特定市町村に
# 属さない係争地のため、いずれの管区にも割り当てない。
OKINAWA_MUNICIPALITY_GROUPS = {
    "那覇": ["那覇市"],
    "北部": [
        "名護市", "本部町", "国頭村", "大宜味村", "東村",
        "今帰仁村", "伊江村", "伊平屋村", "伊是名村",
    ],
    "中部": [
        "宜野湾市", "沖縄市", "うるま市", "恩納村", "宜野座村", "金武町",
        "読谷村", "嘉手納町", "北谷町", "北中城村", "中城村",
    ],
    "南部": [
        "浦添市", "糸満市", "豊見城市", "南城市", "南風原町", "八重瀬町",
        "与那原町", "西原町", "久米島町", "渡嘉敷村", "座間味村", "粟国村",
        "渡名喜村", "南大東村", "北大東村",
    ],
    "宮古": ["宮古島市", "多良間村"],
    "八重山": ["石垣市", "竹富町", "与那国町"],
}

REGION_GROUPS_BY_PREFECTURE = {
    "京都府": {
        "city_name": "京都市",
        "ward_groups": KYOTO_CITY_WARD_GROUPS,
        "municipality_groups": KYOTO_HEALTH_CENTER_MUNICIPALITY_GROUPS,
    },
    "神奈川県": {"city_name": None, "ward_groups": {}, "municipality_groups": KANAGAWA_MUNICIPALITY_GROUPS},
    "福井県": {"city_name": None, "ward_groups": {}, "municipality_groups": FUKUI_MUNICIPALITY_GROUPS},
    "沖縄県": {"city_name": None, "ward_groups": {}, "municipality_groups": OKINAWA_MUNICIPALITY_GROUPS},
}


def build(municipalities_path: str, prefecture: str) -> dict:
    config = REGION_GROUPS_BY_PREFECTURE[prefecture]
    data = json.load(open(municipalities_path, encoding="utf-8"))

    by_ward, by_municipality = {}, {}
    for f in data["features"]:
        props = f["properties"]
        geom = shape(f["geometry"])
        if not geom.is_valid:
            # 離島部などで自己交差する無効なポリゴンが混じっていることがあるため修復する
            geom = geom.buffer(0)
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
