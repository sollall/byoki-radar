"""Enum masters for Validation層 (spec section 5.1).

These lists are PoC-stage placeholders covering only the five MVP
municipalities (spec section 9). They must be verified against each
municipality's official region/disease naming before being treated as
authoritative, and extended as more municipalities are onboarded.
"""

# report_type: "sentinel" = 定点当たり報告数, "case_based" = 全数把握（実数のみ）
DISEASES = {
    "influenza": {"label": "インフルエンザ", "report_type": "sentinel"},
    "covid19": {"label": "COVID-19", "report_type": "sentinel"},
    "rs_virus": {"label": "RSウイルス感染症", "report_type": "sentinel"},
    "gastroenteritis": {"label": "感染性胃腸炎", "report_type": "sentinel"},
    "hand_foot_mouth": {"label": "手足口病", "report_type": "sentinel"},
    "streptococcal_pharyngitis": {"label": "A群溶連菌咽頭炎", "report_type": "sentinel"},
    "chickenpox": {"label": "水痘", "report_type": "sentinel"},
    "measles": {"label": "麻しん", "report_type": "case_based"},
}

ALL_REGION = "ALL"

# region masters per prefecture/municipality (直接パース対象のみ, spec 3.2)
REGION_MASTERS = {
    "神奈川県": {
        ALL_REGION,
        "横須賀三崎", "鎌倉", "藤沢", "平塚", "厚木", "小田原", "松田",
        "横浜市", "川崎市", "相模原市", "藤沢市", "茅ヶ崎市", "厚木市", "大和市",
    },
    "千葉市": {ALL_REGION, "千葉市"},
    "北九州市": {ALL_REGION, "北九州市"},
    "京都府": {
        ALL_REGION,
        "乙訓", "山城北", "山城南", "南丹", "中丹西", "中丹東", "丹後", "京都市",
    },
    "沖縄県": {
        ALL_REGION,
        "那覇", "中部", "北部", "宮古", "八重山", "南部",
    },
}

# 定点当たり報告数の妥当性チェック上限 (spec 5.2)
PER_SENTINEL_MAX = 200

# 前週比の急変を人間レビューに回す倍率閾値 (spec 5.2)
WEEK_OVER_WEEK_FLAG_RATIO = 10

DIRECT_PARSE_PREFECTURES = list(REGION_MASTERS.keys())
