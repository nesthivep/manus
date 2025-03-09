[English](README.md) | [中文](README_zh.md) | 日本語

<p align="left">
    <a href="https://discord.gg/6dn7Sa3a"><img src="https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat" alt="Discord Follow"></a>
</p>

# 👋 OpenManus

Manusは素晴らしいですが、OpenManusは招待コードなしであらゆるアイデアを実現できます 🛫！

私たちのチームメンバー [@mannaandpoem](https://github.com/mannaandpoem) [@XiangJinyu](https://github.com/XiangJinyu) [@MoshiQAQ](https://github.com/MoshiQAQ) [@didiforgithub](https://github.com/didiforgithub) [@stellaHSR](https://github.com/stellaHSR)
および [@Xinyu Zhang](https://x.com/xinyzng) は [@MetaGPT](https://github.com/geekan/MetaGPT) などから来ています。プロトタイプは3時間以内に立ち上げられ、私たちは継続的に構築しています！

これはシンプルな実装ですので、あらゆる提案、貢献、フィードバックを歓迎します！

OpenManusで自分のエージェントを楽しんでください！

また、UIUCとOpenManusの研究者が共同で開発した、強化学習（RL）ベースの（例えばGRPO）LLMエージェントのチューニング方法に特化したオープンソースプロジェクト [OpenManus-RL](https://github.com/OpenManus/OpenManus-RL) を紹介することに興奮しています。

## プロジェクトデモ

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## インストールガイド

インストール方法は2つあります。方法2（uvの使用）を推奨します。これにより、インストールが速くなり、依存関係の管理が向上します。

### 方法1：condaの使用

1. 新しいconda環境を作成します：

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. リポジトリをクローンします：

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. 依存関係をインストールします：

```bash
pip install -r requirements.txt
```

### 方法2：uvの使用（推奨）

1. uv（高速なPythonパッケージインストーラー）をインストールします：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. リポジトリをクローンします：

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. 新しい仮想環境を作成してアクティブにします：

```bash
uv venv
source .venv/bin/activate  # Unix/macOSの場合
# Windowsの場合：
# .venv\Scripts\activate
```

4. 依存関係をインストールします：

```bash
uv pip install -r requirements.txt
```

## 設定

OpenManusは使用するLLM APIの設定が必要です。以下の手順に従って設定を行ってください：

1. `config`ディレクトリに`config.toml`ファイルを作成します（例からコピーできます）：

```bash
cp config/config.example.toml config/config.toml
```

2. `config/config.toml`を編集してAPIキーとカスタム設定を追加します：

```toml
# グローバルLLM設定
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 実際のAPIキーに置き換えてください
max_tokens = 4096
temperature = 0.0

# 特定のLLMモデルのオプション設定
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # 実際のAPIキーに置き換えてください
```

## クイックスタート

OpenManusを一行で実行：

```bash
python main.py
```

その後、ターミナルでアイデアを入力してください！

開発中のバージョンを体験するには、以下を実行してください：

```bash
python run_flow.py
```

## 貢献方法

あらゆる友好的な提案や有益な貢献を歓迎します！issueを作成するか、pull requestを提出してください。

または、📧メールで @mannaandpoem に連絡してください：mannaandpoem@gmail.com

## ロードマップ

コミュニティメンバーからのフィードバックを総合的に収集した後、3〜4日をサイクルとする反復モードを採用し、期待される機能を段階的に実現することにしました。

- [ ] プランニング能力の強化、タスク分解と実行ロジックの最適化
- [ ] 標準化された評価指標の導入（GAIAおよびTAU-Benchに基づく）による継続的なパフォーマンス評価と最適化
- [ ] モデル適応の拡大と低コストアプリケーションシナリオの最適化
- [ ] コンテナ化されたデプロイメントの実現、インストールと使用ワークフローの簡素化
- [ ] 実用的なケースを含む例のライブラリの充実、成功と失敗の例の分析を含む
- [ ] ユーザーエクスペリエンスの向上のためのフロントエンド/バックエンド開発

## コミュニティグループ

Feishuのネットワーキンググループに参加して、他の開発者と経験を共有しましょう！

<div align="center" style="display: flex; gap: 20px;">
    <img src="assets/community_group.jpg" alt="OpenManus 交流群" width="300" />
</div>

## Star数の履歴

[![Star History Chart](https://api.star-history.com/svg?repos=mannaandpoem/OpenManus&type=Date)](https://star-history.com/#mannaandpoem/OpenManus&Date)

## 謝辞

このプロジェクトに基本的なサポートを提供してくれた [anthropic-computer-use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
および [browser-use](https://github.com/browser-use/browser-use) に感謝します！

OpenManusはMetaGPTコミュニティの貢献者によって構築されています。このエージェントコミュニティに感謝します！
