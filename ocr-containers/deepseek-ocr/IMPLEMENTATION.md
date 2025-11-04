# DeepSeek OCR スキーマ変換実装ドキュメント

## 概要

DeepSeek OCRの出力（グラウンディングタグ付きMarkdown）をPaddleOCR互換のJSONスキーマに変換する機能を実装しました。

## 実装ファイル

### 1. model_handler.py

DeepSeek OCRの出力をPaddleOCR形式に変換する主要な関数を実装。

#### 主要関数

##### `convert_deepseek_to_paddle_schema(markdown_text, image_width, image_height)`

DeepSeekのグラウンディングタグ付きMarkdownをPaddleOCR互換スキーマに変換。

**入力:**
```markdown
<|ref|>table<|/ref|><|det|>[[40, 55, 963, 135]]<|/det|>
<table><tr><td>氏名</td><td>日本</td><td>花子</td></tr></table>
```

**出力:**
```json
{
  "words": [
    {
      "id": 0,
      "content": "氏名 日本 花子",
      "rec_score": 1.0,
      "points": [[40, 55], [963, 55], [963, 135], [40, 135]]
    }
  ]
}
```

**処理フロー:**
1. 正規表現で`<|ref|>...<|/ref|><|det|>[[...]]<|/det|>`パターンをマッチング
2. 座標を抽出してパース（カンマ区切りの4つの数値）
3. 座標を正規化解除（0-999 → 実ピクセル座標）
4. 2点座標を4点座標に変換（矩形の4隅）
5. HTMLタグを除去してプレーンテキスト化
6. PaddleOCR形式のJSONを構築

##### `extract_text_from_html(html_content)`

HTML文字列からプレーンテキストを抽出。

**処理内容:**
- `<br>`, `</tr>`, `</td>` をスペースに置換
- その他のHTMLタグを除去
- 連続する空白を1つのスペースに統合

##### `format_ocr_result(extracted_text, image_width, image_height)`

既存のインターフェースを維持しつつ、内部で`convert_deepseek_to_paddle_schema`を呼び出す。

## 座標変換の詳細

### 正規化解除

DeepSeekは0-999の正規化座標を使用するため、実ピクセル座標に変換：

```python
actual_x = int((x / 999.0) * image_width)
actual_y = int((y / 999.0) * image_height)
```

### 4点座標への変換

DeepSeekの2点座標 `[x1, y1, x2, y2]` を4点座標に変換：

```python
points = [
    [actual_x1, actual_y1],  # 左上
    [actual_x2, actual_y1],  # 右上
    [actual_x2, actual_y2],  # 右下
    [actual_x1, actual_y2]   # 左下
]
```

## テスト

### test_converter.py

変換関数の単体テストスクリプト。

**実行方法:**
```bash
cd /Users/sabamiso/develop/sample-auto-extract-ai-ocr-app/ocr-containers/deepseek-ocr
python test_converter.py
```

**テスト内容:**
- 実際のDeepSeek出力データを使用
- スキーマ検証（必須フィールドの存在確認）
- 座標変換の正確性確認
- JSON出力の確認

## エラーハンドリング

### 座標パースエラー
- 座標が4つの数値でない場合はスキップ
- ログに警告を出力

### HTML解析エラー
- HTMLタグ除去に失敗しても処理を継続
- 空のコンテンツは結果から除外

### 全体エラー
- 変換全体が失敗した場合は空の`words`配列を返す
- エラーログを出力

## 統合

### app.py との統合

`app.py`の`perform_ocr`関数内で自動的に呼び出される：

```python
# DeepSeek推論実行
res = model.infer(...)

# 変換関数を呼び出し
result = format_ocr_result(res, image.width, image.height)

# PaddleOCR互換形式を返却
return result
```

## Lambda APIとの互換性

変換後のスキーマはPaddleOCRと完全互換のため、Lambda APIの既存コードは変更不要：

- `lambda/api/app/ocr.py` の `perform_ocr()` がそのまま使用可能
- `lambda/api/app/schemas.py` の `OcrWord` と `OcrResult` に適合
- `/result/{image_id}` エンドポイントで正しく返却される

## 制限事項

1. **rec_score**: DeepSeekは信頼度スコアを提供しないため、固定値1.0を使用
2. **グラウンディングタグ必須**: タグがないテキストは検出されない
3. **座標精度**: 正規化座標（0-999）のため、小さい画像では精度が低下する可能性

## 今後の改善案

1. グラウンディングタグがないプレーンテキストのサポート
2. 信頼度スコアの推定ロジック追加
3. より複雑なHTML構造への対応（ネストされたテーブル等）
4. パフォーマンス最適化（大量のテキストブロック処理）

## 参考資料

- DeepSeek OCR: https://github.com/deepseek-ai/DeepSeek-OCR
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- サンプル出力: `/Users/sabamiso/Downloads/out/result_ori.md`
