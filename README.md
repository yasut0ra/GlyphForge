# GlyphForge — Shape-aware ASCII Art Lab

自然言語またはアップロード画像から、glyphの**形**を比較して ASCII Art / AA を作るローカルMVPです。LLMに完成AAを直接書かせず、Visual Planと参照線画を経由し、最終AAを固定幅フォントで再描画して損失を最適化します。

## クイックスタート

必要環境は Python 3.11+ と Node.js 22.13+ です。

```bash
make setup
```

ターミナルを2つ開き、APIとWeb UIを起動します。

```bash
make api
```

```bash
make web
```

ブラウザで `http://localhost:3000` を開きます。画像生成APIがなくても、画像アップロードからの変換と、猫・宇宙船・アニメ人物などのオフライン参照線画デモが動作します。

ポートや公開URLを変える場合は `frontend/.env.local` に `NEXT_PUBLIC_API_URL` と `NEXT_PUBLIC_SITE_URL` を設定できます（例は `frontend/.env.example`）。

## Architecture

```text
自然言語 / アップロード画像
        │
        ▼
Visual Planner ── structured VisualPlan
        │
        ▼
ImageGenerationProvider ── high-contrast reference
        │
        ▼
preprocessing ── grayscale / contrast / character-aware resize
        │
        ▼
GlyphLibrary ── raster patch / density / edge / orientation
        │
        ▼
initial matcher ── per-cell top-k glyph candidates
        │
        ▼
monospace re-render ── reconstruction loss
        │
        ▼
HillClimbOptimizer ── 1 glyph replacement in 3×3 neighborhoods
        │
        ▼
optimized AA + rendered preview + metrics
```

```text
frontend/                     Vinext / Next.js-compatible React / TypeScript / Tailwind
backend/
  app/
    api/                      FastAPI routes only
    planner/                  LLMProvider + local/OpenAI planners
    image_generation/         replaceable reference-image providers
    glyphs/                   charset config, glyph rasterization, descriptors
    renderer/                 preprocessing, matching, re-rendering, loss
    optimizer/                Optimizer interface + hill climbing
    evaluator/                SemanticEvaluator interface + structural proxy
    models/                   API schemas
    service.py                end-to-end orchestration
  config/charsets.json        style/detail-specific configurable charsets
  tests/
```

API routeには画像処理を置かず、route → pipeline service → domain modules の順に責務を分離しています。`Optimizer` は simulated annealing / genetic algorithm / MCTS / discrete diffusion へ、3つのprovider interfaceは別実装へ差し替えられます。

## Algorithm

### 1. Glyph rendering

`GlyphLibrary` は選択charsetの各文字を同じ固定幅フォント・同じ `12×22px` セルに事前レンダリングし、以下をキャッシュします。

- pixel patch（inkを1、背景を0に正規化）
- density
- gradient edge map
- 4方向のorientation histogram

そのため `/`、`\\`、`_`、`|`、括弧、罫線、ブロック文字は、単なる明るさではなく実際にレンダリングされた形で比較されます。charsetは [`backend/config/charsets.json`](backend/config/charsets.json) だけで変更できます。

### 2. Image preprocessing

入力をEXIF補正してグレースケール化し、contrast強調とunsharp maskを適用します。画像の縦横比とglyphセルの縦横比から行数を自動計算し、余白を白で保ったままターゲットグリッドへ収めます。

### 3. Initial matching

各ターゲットセルと全glyph patchを比較し、次の局所損失で最良文字と上位候補を保存します。

```text
local_loss =
    0.54 * pixel_loss
  + 0.23 * edge_loss
  + 0.18 * orientation_loss
  + 0.05 * density_loss
```

### 4. Re-render and optimization

選択文字のpatchを連結してAA全体を画像へ戻し、ターゲットと比較します。

```text
reconstruction_loss =
    0.58 * pixel_loss
  + 0.30 * edge_loss
  + 0.12 * orientation_loss
```

初期AAの誤差が大きいセルから、上位候補への1文字置換を試します。各候補は対象セルを中心とする `3×3` セル領域で再描画・再評価し、さらに全体損失が改善した変更だけを採用します。詳細度に応じて1〜3 pass実行します。

### 5. Evaluation

レスポンスには次を含みます。

- initial / optimized reconstruction loss
- accepted iterations / candidate evaluations
- generation time / character count
- SSIM
- edge similarity
- structural semantic proxy score

`SemanticEvaluator` は現在API不要のstructure proxyです。VLMやvision encoderを使う実装に差し替えられるinterfaceを用意しています。

## AI API設定（任意）

```bash
cp backend/.env.example backend/.env
```

`backend/.env` に以下を設定し、`backend` ディレクトリで環境を読み込んで起動します。

```bash
set -a
source .env
set +a
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```dotenv
OPENAI_API_KEY=...
OPENAI_PLANNER_MODEL=gpt-5.4-mini
OPENAI_IMAGE_MODEL=gpt-image-1
```

- `OPENAI_API_KEY` あり: Responses APIのStructured OutputsでVisual Planを作り、画像未指定時はImages APIで参照線画を生成します。
- キーなし: local heuristic planner + offline procedural line artを使います。
- 画像アップロードあり: 画像生成providerを使わず、その画像から後続処理を実行します。
- 外部APIに失敗した場合もローカルproviderへフォールバックします。

キーはバックエンドだけに置き、`NEXT_PUBLIC_` 変数には入れないでください。実装は公式の [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create) と [GPT Image 1](https://developers.openai.com/api/docs/models/gpt-image-1) の仕様に沿っています。

## API

FastAPIの対話ドキュメントは `http://localhost:8000/docs` です。

```text
GET  /api/health
POST /api/plan       multipart: prompt, width, style, detail
POST /api/generate   multipart: prompt, width, style, detail, image?
```

`style` は `pure_ascii | unicode | block`、`detail` は `simple | normal | detailed` です。幅は20〜120文字、画像は12MBまでです。

```bash
curl -X POST http://localhost:8000/api/generate \
  -F 'prompt=宇宙船をレトロなASCII Artで' \
  -F 'width=60' \
  -F 'style=pure_ascii' \
  -F 'detail=normal'
```

## Verification

```bash
make test
make build
```

テストは幅保持、charset制約、画像→AA→画像、最適化後lossが初期loss以下であることを検証します。

## MVPの制約と今後の改善

- glyph patchは現在単一フォントです。Unicodeの表示幅・font fallbackを厳密に扱うには、ブラウザとバックエンドで同一のWeb fontを同梱し、wcwidth検証を追加します。
- SSIMはMVP向けのglobal approximationです。OpenCV/scikit-imageによるwindowed SSIMへ交換できます。
- initial matchingをlandmark-awareにし、顔・目・輪郭の重みを別々に最適化できます。
- 3×3 coordinate searchをbeam search、simulated annealing、genetic algorithm、MCTS、discrete diffusionへ拡張できます。
- CLIP/SigLIP/VLM evaluator、aesthetic model、complexity penaltyを統合し、複数目的Pareto探索にできます。
- glyph間の連結性、左右対称prior、負の空間、行間をglobal constraintsとして追加できます。
- 生成結果の保存、seed固定、custom charset編集、複数候補比較は次のUI拡張候補です。
