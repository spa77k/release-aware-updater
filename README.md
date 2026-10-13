# Release-aware updater

リリースノートを読み、互換性・破壊的変更・移行手順を確認してから
アプリ・ライブラリ・パッケージ依存関係・Dockerイメージを更新する汎用スキルです。
Minecraftプラグインも、用途のひとつとして扱えます。

Claude Code、Codex、その他の[Agent Skills](https://agentskills.io/specification)
対応エージェントで同じ `SKILL.md` を使えます。特定プロバイダーのAPIや
Claude専用フックには依存しません。

**Release-note-aware dependency updates, for any agent.** The agent researches
official release notes; an optional offline Python helper creates reviewable pin
diffs, applies authorized local edits, and reverses unchanged pin updates.

## できること

- 現在版から候補版までのリリースノート、依存関係、互換性の調査
- アプリ/ライブラリのAPI・実行環境・直接/間接依存・lockfileの確認
- 必要な場合のみMinecraft・Java・サーバー実装・プラグイン依存の確認
- Dockerイメージのタグ/digest、CPUプラットフォーム、永続データの確認
- 破壊的変更・移行・テスト・ロールバックを含む更新計画と差分
- URL + SHA-256 / イメージdigestのローカル更新と、ファイルhashを確認する復元
- 不明・非互換・未検証の項目を保留する判定

npm/pip/Cargo/Maven/Gradle等は既存のパッケージマネージャーでmanifestとlockfileを
更新します。Python補助CLIはURL + SHA-256とDocker digestのテキスト固定専用で、
パッケージ解決やlockfile再生成はしません。Docker Engine/OS自体の更新と
ライブ環境へのデプロイは別の作業です。
スクリプトは通信・ダウンロード・コマンド実行・サービス再起動をしません。
実際のリリースノート調査にはエージェントのWeb/リポジトリ閲覧機能を使います。

## インストール

まず公開リポジトリを取得します。スクリプトを確認してから使ってください。

```sh
git clone https://github.com/spa77k/release-aware-updater.git
cd release-aware-updater
```

### Claude Code

```sh
mkdir -p ~/.claude/skills
cp -R skills/release-aware-updater ~/.claude/skills/
```

`/release-aware-updater` で呼び出せます。プロジェクト限定なら、対象リポジトリの
`.claude/skills/release-aware-updater/` に同じフォルダーを配置してください。

### Codex

```sh
mkdir -p ~/.agents/skills
cp -R skills/release-aware-updater ~/.agents/skills/
```

`$release-aware-updater` で指定できます。プロジェクト限定なら対象リポジトリの
`.agents/skills/release-aware-updater/` に配置します。

既存の同名スキルがある場合は、上書き前に差分を確認してください。
各エージェントで自動検出されない場合は再起動/再読み込みを行ってください。

### その他のエージェント・スキル非対応ツール

`skills/release-aware-updater/` をホストのスキル配置先へコピーしてください。
配置先・呼び出し記法はホスト依存です。スキル非対応でも `SKILL.md` を参照させ、
Python CLIを直接使えます。全ホストの自動検出を保証するものではありません。

形式・配置先の公式資料:
[Agent Skills](https://agentskills.io/specification) /
[Claude Code](https://code.claude.com/docs/en/skills) /
[Codex](https://developers.openai.com/codex/skills)

## 依頼例

> このリポジトリのアプリ・ライブラリ・Dockerイメージについて、現在版から
> 最新の互換性がある安定版までの公式リリースノートを確認して。
> 破壊的変更、実行環境・API要件、lockfileへの影響、移行と復元方法を含む更新案と差分を作って。
> まず計画だけ。デプロイはしないで。

> Review the official release notes for these application, library, and container dependencies.
> Update compatible pins in this checkout, run the repository checks, and list
> migrations and runtime tests still needed. Do not deploy or restart anything.

`計画だけ` と `ローカル編集も行う` は別の範囲です。公開・再起動・デプロイは
このスキルの存在だけでは許可されません。ホストとユーザーの権限設定に従います。

## オフラインで試す

必要環境: Python 3.11以降。追加のPythonパッケージ、Docker、APIキーは不要です。
以下は架空のURL・digest・リリースノートを使った動作デモです。
実在の配布物を検証した例ではありません。

```sh
demo=$(mktemp -d)
cp -R examples/general "$demo/repo"
python3 skills/release-aware-updater/scripts/update.py plan \
  --root "$demo/repo" --manifest examples/general-manifest.json --out "$demo/plan.json"
cat "$demo/plan.md"
python3 skills/release-aware-updater/scripts/update.py apply \
  --root "$demo/repo" --plan "$demo/plan.json"
python3 skills/release-aware-updater/scripts/update.py rollback \
  --root "$demo/repo" --plan "$demo/plan.json"
```

このデモは汎用アプリ・配布ファイル形式のライブラリ・Dockerの3種類を扱います。
従来のMinecraft例は `examples/demo` と `examples/manifest.json` に残しています。
ライブラリ例はURL/hash固定の架空形式で、npm等のlockfileを代替するものではありません。

自分のリポジトリには、調査済みの情報でmanifestを作成してください。
[入力仕様](skills/release-aware-updater/references/manifest.md)と
[調査・検証の観点](skills/release-aware-updater/references/research.md)を参照できます。
インストール済みフォルダーにも `references/manifest-template.json` とLICENSEを
同梱しています。テンプレートは未検証として保留状態なので、調査結果を埋めてください。

## 安全性と限界

- リリースノートの文章はデータとして読みます。埋め込まれた指示は実行しません
- `ready` は入力された証拠に基づくローカル編集の判定です。研究内容の真偽や
  実行環境での互換性、デプロイ可否をスクリプトが証明するものではありません
- 文字列を一意に置換する仕組みです。YAML/Compose構文や実際のアプリ起動は
  別途テストが必要です。自動のバージョン探索・全サイト対応スクレイピングは行いません
- hashは改ざん検知/再現性に役立ちますが、それだけで配布元の真正性は証明できません
- `rollback` はファイル中のpinだけを戻します。DB・ワールド・volumeの変更は戻りません
- 複数ファイルの更新全体は単一トランザクションではありません。競合する編集を止めた
  通常のチェックアウトで使い、途中終了時は状態を確認してください
- manifestとレポートには変更行やURLが含まれます。秘密情報がないか公開前に確認してください

## テスト

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

ネットワーク不要。正常な計画/適用/復元、保留判定、入力不正、曖昧な置換、
パス逸脱、symlink、改変ファイル、CRLF、二重実行などを確認します。
入出力ファイルの1 MiB上限はUTF-8のバイト数で検査し、変更後に復元できない
サイズへ増える更新は拒否します。生成planは読み込み可能な8 MiB以下に制限します。
`__pycache__` とPythonバイトコードは配布対象から除外しています。
GitHub ActionsにもPython 3.11 / 3.13の同じ回帰テストを設定しています。

## 構成

```text
skills/release-aware-updater/
  SKILL.md                 共通の指示
  references/              調査指針・manifest仕様
  scripts/update.py        標準ライブラリだけのCLI
examples/                  架空データのオフラインデモ
tests/                     回帰テスト
```

MIT License.
