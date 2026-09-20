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
    # 神奈川県衛生研究所の実CSV(疾患ごと・年ごと配布)で確認した地域名。
    # "全県"は県全体集計だが、既存のALL_REGION("ALL")とは表記が異なるため
    # 別名として丸めず、そのまま許可地域として登録する(spec 5.1: 推測で丸めない)。
    "神奈川県": {
        ALL_REGION,
        "全県", "県域",
        "横浜市", "川崎市", "相模原市", "横須賀市", "藤沢市", "茅ケ崎市",
        "平塚", "平塚　秦野センター", "鎌倉", "鎌倉　三崎センター",
        "小田原", "小田原　足柄上センター", "厚木", "厚木　大和センター",
    },
    "千葉市": {ALL_REGION, "千葉市"},
    "北九州市": {ALL_REGION, "北九州市"},
    # 京都府感染症情報センターの実CSV(発生地図用)で確認した地域名。
    # 京都市内は行政区ではなく保健所管区(5区分)単位で集計されている。
    "京都府": {
        ALL_REGION,
        "乙訓", "山城北", "山城南", "南丹", "中丹西", "中丹東", "丹後",
        "北・左京", "上京・中京・下京", "東山・山科", "南・伏見", "右京・西京",
    },
    "沖縄県": {
        ALL_REGION,
        "那覇", "中部", "北部", "宮古", "八重山", "南部",
    },
    "山梨県": {ALL_REGION},
}

# 定点当たり報告数の妥当性チェック上限 (spec 5.2)
PER_SENTINEL_MAX = 200

# 前週比の急変を人間レビューに回す倍率閾値 (spec 5.2)
WEEK_OVER_WEEK_FLAG_RATIO = 10

DIRECT_PARSE_PREFECTURES = list(REGION_MASTERS.keys())
