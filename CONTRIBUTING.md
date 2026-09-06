# Contributing to GlyphForge

GlyphForgeへの改善提案を歓迎します。小さな修正を除き、実装前にIssueで目的と方針を共有してください。

## 開発環境

- Python 3.11以上
- Node.js 22.13以上

```bash
make setup
make api
make web
```

Web UIは `http://localhost:3000`、APIドキュメントは `http://localhost:8000/docs` で確認できます。OpenAI APIキーは必須ではありません。

## 変更時の確認

Pull Requestを作る前に、次を実行してください。

```bash
make test
cd frontend && npm run lint && npm run build
```

画像処理や最適化を変更する場合は、少なくとも次を維持してください。

- 最終AAをglyph画像として再レンダリングして評価すること
- pixel・edge・orientationを損失に含めること
- optimized reconstruction lossがinitial lossより悪化しないこと
- Pure ASCIIでASCII printable characters以外を出力しないこと

## Pull Request

- 1つのPRには、できるだけ1つの目的だけを含めてください。
- 変更理由、確認方法、UI変更時はbefore/afterを記載してください。
- 新しい環境変数は対応する `.env.example` とREADMEにも追加してください。
- APIキー、生成物に含まれる個人情報、ローカルの絶対パスをコミットしないでください。

セキュリティ上の問題は公開Issueに投稿せず、[SECURITY.md](SECURITY.md)の手順を利用してください。
