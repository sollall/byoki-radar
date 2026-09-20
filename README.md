# byoki-radar

国内の感染症発生動向（定点当たり報告数）を都道府県・保健所管区レベルで可視化する
Webサービスの PoC/MVP実装。仕様は [`SPEC.md`](./SPEC.md) を参照。

## 実装範囲 (MVP)

仕様書 9章の方針に沿い、MVPは「直接パース」区分の5自治体のみを対象とする。

- 神奈川県（CSV, 保健所管区別）
- 千葉市（CSV, 市全体）
- 北九州市（CSV, 市全体）
- 京都府（HTML表, 保健所別）
- 沖縄県（Excel, 保健所別）

LLM抽出対象（PDF/自然文の自治体）は後続フェーズ。

5層構成（Raw / Extract / Validation / Store / Map）のうち、Raw層の実際のクロール
（各自治体サイトへの定期HTTP取得）は未実装。`backend/fixtures/` に
**パイプライン動作確認用の架空のサンプルデータ**を置き、Raw層の代わりとしている。
実データを使う場合は `backend/app/seed.py` の `SOURCES` を実URL取得結果に差し替える。

## 構成

```
backend/
  app/
    masters.py      # Validation層のenumマスタ (5.1)
    db.py            # Store層のテーブル定義 (4章, SQLite)
    schemas.py       # Extract層の出力スキーマ
    validation.py    # Validation層のルール (5章)
    extract/         # 自治体ごとのExtractパーサ (3章)
    seed.py          # Raw(fixtures)->Extract->Validation->Store を実行
    api.py           # Map層向けAPI (7章)
  fixtures/          # サンプル生データ (Raw層相当)
  tests/
frontend/
  index.html/app.js/style.css  # Leafletによる地図表示
  japan.geojson                # 都道府県境界 (dataofjapan/land を簡略化)
  vendor/leaflet/              # Leaflet本体 (CDN非依存にするため同梱)
```

## セットアップと起動

依存関係の管理・実行には [uv](https://docs.astral.sh/uv/) を使用する。

```bash
cd backend
uv sync

# サンプルデータをExtract->Validation->Storeまで流し込む
uv run python -m app.seed

# API起動
uv run uvicorn app.api:app --port 8811
```

別ターミナルでフロントを配信:

```bash
cd frontend
python3 -m http.server 8812
```

`http://localhost:8812/index.html` を開く。API のURLは `frontend/app.js` の
`window.BYOKI_RADAR_API_BASE`（未設定時は `http://localhost:8811`）で変更できる。

## テスト

```bash
cd backend
uv run pytest
```

Validation層の各ルール（未知region/diseaseのflag、定点当たり報告数の範囲チェック、
前週比10倍以上のflag、同一ソース内での抽出結果の割れ検出）と、5自治体分の
Extractパーサが fixtures を正しくパースできることを検証している。

## 仕様との対応・既知の未実装事項

- **Raw層の定期取得・Dagster asset chain (8章)**: 未実装。`seed.py` が手動実行の代替。
- **patient_count / per_sentinel_count の整合性チェック (5.2)**: 保健所別の定点数
  マスタが未整備のため未実装。
- **LLM抽出 (3章)**: 未実装。直接パース対象のみ。
- **flaggedレコードの人間レビューフロー (10章)**: 未実装。`validation_status=flagged`
  のレコードはDBに保存されるが、レビューUIは無い。
- **region/diseaseマスタ (`app/masters.py`)**: PoC段階のプレースホルダー。本番投入前に
  各自治体の公式表記と突き合わせて検証・拡充が必要。
- 保健所管区レベルの地図ポリゴンは未整備のため、地図は都道府県単位の色分け＋
  クリックで管区別内訳テーブルを表示するドリルダウン方式とした。
