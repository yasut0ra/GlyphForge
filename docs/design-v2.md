# Renderer v2: 評価した文字配置をそのまま使う

## 決定

Visual Plan → 参照画像 → glyph探索という流れを維持し、描画の共通仕様と空間的な損失を中心に組み直す。外部AI API・学習データ・追加画像処理ライブラリを増やさず、手元で比較検証できる改善を優先した。

```text
Prompt / uploaded image + width + style + detail + render profile
    → Visual Plan / reference provider
    → canonical reference（透明部分を白へ合成、最大900px）
    → shared render contract（font / advance / baseline / line height）
    → aspect-aware target grid
    → multiscale glyph candidates
    → exact-delta coordinate search
    → detailed / feedback: bounded joint two-cell search
    → text + reference + actual glyph raster + loss / structure metrics
    → optional browser Canvas evaluation → same-contract refinement
```

## 旧方式でずれていた点

1. 各glyphのbounding boxをセル中央へ移動していた。ピリオド、下線、英字の上下位置が通常のテキストと一致せず、最適化対象の画像をコピー先で再現できなかった。
2. Notes向けにコピー段階で列を1.32倍へ複製していた。AAを評価した後に別の文字グリッドへ変換しており、指定幅も変わっていた。
3. 全画像のorientation histogramは位置情報を失う。局所窓でのスコアと全体スコアが一致せず、候補ごとに大きな画像を評価し直していた。
4. `1 - mean(edge difference)`は背景の多い画像で空白も高得点になる。UIの初期AA、プレビュー、スコアも別々の固定値だった。

## 描画の共通仕様

`frontend/lib/render-contract.json`をPythonとTypeScriptの両方が読む。フォントは`frontend/public/fonts/DejaVuSansMono.ttf`を同梱し、OSに依存した自動フォント選択をなくした。ライセンス全文も同梱する。

| 項目 | Code / Terminal | Notes / Docs |
|---|---:|---:|
| Font size（基準px） | 20 | 20 |
| Cell width | 12 | 12 |
| Line height | 24 | 30 |
| Baseline | 19 | 22 |

Notes / Docsは「広めの行間を使う等幅テキスト」のプリセットであり、各アプリの自動検出結果ではない。生成前に選び、行数を参照画像の縦横比から計算する。生成後に選択を変えても、表示済み結果の描画仕様は変わらない。

Pillowは共通ベースラインへ描画する。ブラウザは同一TTFとfont metrics override、フォントの小数advanceを補う微小なletter-spacingを使用する。Canvasは明示的な列座標とベースラインを使う。アンチエイリアス、hinting、1px未満の字形のはみ出しは描画エンジンで異なるため、ピクセル完全一致を保証する仕様ではない。Pillowで普通の1行テキストを描いた独立オラクルとglyph patchの差をテストする。

Unicodeはフォントに実在する等幅glyphだけを許可する。結合文字・全角文字・欠損glyphは除外し、APIの`warnings`で知らせる。Pure ASCIIはprintable ASCIIのまま。

コピーでは全行共通の外側余白だけを取り除き、内部空白・空行・文字を保持する。プレーンテキストでは文字複製や特殊空白への置換はしない。リッチコピーのHTMLには空白保持用のnon-breaking spaceを使う。外部アプリがフォント・空白・改行を変更すればテキストは崩れる。リッチコピーは等幅書式を要求するが強制できない。画像としての再現が必要な場合はPNGを使う。

## 損失と探索

`MultiscaleObjective`は次の空間情報を持つ。

- pixel: 前景近傍の重みを上げた画素二乗誤差
- edge: gradient magnitudeの二乗誤差
- orientation: 各位置のunsigned structure tensorの二乗誤差
- shape: 3×3と9×9の平均化画像の二乗誤差

各項をターゲットのエネルギーで正規化し、線画では重みを`0.25 / 0.15 / 0.10 / 0.20 / 0.30`とする。画像の勾配が小さい場合はedge/orientationの重みを粗いshape項へ移す。平坦な濃淡画像では文字の網点そのものを「不要なエッジ」と過大評価しない。正規化の分母にも前景エネルギーに応じた下限を設ける。この下限なしではBlock Artが空白へ潰れるため、一定濃度の入力を回帰テストに含めた。

初期候補は同じ種類の特徴をセル単位で比較する。ただし初期化の正規化は各セルに局所的であり、全体目的関数の独立な最適解ではない。探索では**ターゲット全体で固定した正規化**を使用する。

各損失は画素ごとの寄与の和で、最大フィルタ半径は4px。文字置換時に変化する領域とhaloだけを再計算すれば、全画像の再評価と同じ差分が得られる。境界の切り抜き誤差を避けるため、寄与範囲とフィルタ計算範囲に2段階のhaloを設ける。テストで全画像再描画の差分と照合する。各pass後にも全体損失を記録する。

通常生成はcoordinate searchを使う。Detailedとフィードバック再探索には、隣接2セルの上位候補の直積を調べる予算付き探索を用意した。単独置換では越えられない局所解を対象にする拡張だが、今回の通常線画ベンチマークでは追加の同時置換は採用されなかったため、Normal/Simpleでは予算を0にして余分な計算を避ける。

`optimizer/hill_climb.py`と`legacy_reconstruction_loss`は旧損失・探索の比較用として残す。API経由の生成・改善はv2を使用する。大きな学習器やMCTSを入れる前に、評価する画像と配布するテキストのずれを減らすことを優先した。

## 指標と検証

- reconstruction loss: v2の目的関数。v1の数値との直接比較は不可。
- Edge F1: 1pxの位置許容付きprecision/recall。白い背景の一致を加点しない。線画向けで、勾配のない濃淡ランプでは参考にならない。
- SSIM: 11×11のbox windowによる平均。標準のGaussian-window SSIMと同一ではなく、背景が多い画像では高くなりうる。
- Structure score: SSIMとEdge F1の構造proxy。物体認識や意味的一致の精度ではない。`semantic_score`はAPI互換性のため残すが同じ構造proxyを返す。
- iteration / pass / joint move: 受理した手数、全体走査回数、複数文字を変えた手数を分ける。

再現用: `make test`、`make benchmark`。ベンチマークは猫・宇宙船・人物・非対称の細線・濃淡ランプと2種類の行間、Unicode/Blockのケースを含む12条件。**同じv2フォント、同じ前処理、幅40、同じcharset**で、旧matcher/loss/searchと新matcher/loss/searchだけを比較する。v1リリース全体との比較や、一般画像・人物の認識品質を保証する試験ではない。両方式のlossはv2 objectiveで再評価するため、独立したshape F1・Edge F1・SSIMと出力画像も併記する。

`backend/scripts/generate_sample.py`は実際のオフラインpipelineからUIのサンプル・画像・指標を同時に更新する。APIテストはキーを空に固定し、画像アップロードから生成・評価・再探索まで通信なしで検証する。

数値と比較条件は[実測レポート](benchmark-v2.md)を参照。ローカル描画評価はAAの縦横比を維持し、問題領域の正規化座標を同じ文字グリッドへ返す。別の正方形余白を追加すると探索箇所がずれるため、その変換は行わない。ローカル評価の`subject_score`等は既存APIとの互換フィールドであり、意味認識ではなく構造proxyである。

## 次の判断材料

今回のfixtureは少数であり、人間による比較評価は未実施。広い被写体、40/60/80列、濃い陰影、実際の貼り付け先での評価を増やす。人物の目・髪・ヘッドセットの認識などはこの損失だけでは保証できず、Visual Planのlandmarkを参照画像上の位置・重みに落とす方法を次に検討する。VLMは引き続き問題箇所の指摘に使い、揺れる絶対スコアだけで細かな文字置換を選ばない。

Sources: [DejaVu license](https://dejavu-fonts.github.io/License.html), [Pillow text anchors](https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html).
