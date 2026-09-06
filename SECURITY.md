# Security Policy

## Supported versions

GlyphForgeはMVP段階のため、`main`ブランチの最新版のみをサポートします。

## Reporting a vulnerability

脆弱性や秘密情報の露出を発見した場合は、公開IssueやDiscussionへ詳細を投稿しないでください。GitHubのリポジトリ画面にある **Security → Report a vulnerability** から非公開で報告してください。

報告には、影響範囲、再現手順、想定されるリスク、可能であれば修正案を含めてください。確認前に第三者へ公開することは避けてください。

## API keys and uploaded images

- `OPENAI_API_KEY` は `backend/.env` にだけ保存し、Gitへ追加しないでください。
- `NEXT_PUBLIC_` で始まる変数へ秘密情報を設定しないでください。
- アップロード画像は処理中にメモリ上で扱いますが、機密画像を第三者のAI APIへ送る場合は、そのproviderのデータ取り扱い条件を確認してください。
