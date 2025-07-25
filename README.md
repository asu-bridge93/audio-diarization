# 🎵 音声文字起こしツール（シンプル版）

MP4動画から**話者分離付きの文字起こし**を自動生成するシンプルなツールです。

## ✨ 特徴

- 🎬 **MP4動画対応**: 動画から音声を自動抽出
- 👥 **話者分離**: 誰がいつ話したかを自動識別
- 📝 **日本語文字起こし**: 高精度なWhisper Large V3使用
- 📄 **Markdown出力**: 見やすい形式で結果を保存
- 💻 **2つの使用方法**: コマンドライン版とWeb版
- ⚡ **uv対応**: 高速なパッケージ管理

## 🚀 インストール

### 方法1: uv使用（推奨・高速）

```bash
# uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトをセットアップ
uv sync

# Web版も使いたい場合
uv sync --extra web
```

### 方法2: pip使用

```bash
# 依存関係をインストール
pip install -r requirements.txt
```

## 📁 ファイル構成

```
├── audio_transcriber.py    # コア処理クラス
├── main.py                # コマンドライン版
├── web_app.py             # Streamlit Web版
├── pyproject.toml         # uv用プロジェクト設定
├── requirements.txt       # pip用依存関係
└── README.md             # この説明書
```

## 使用方法

### 1. コマンドライン版（推奨）

#### uv使用
```bash
# 基本的な使用方法
uv run python main.py meeting.mp4

# または、uvでインストールしたスクリプトを直接実行
uv run transcribe meeting.mp4

# 出力ファイル名を指定
uv run python main.py meeting.mp4 -o my_transcript.md
```

#### pip使用
```bash
# 基本的な使用方法
python main.py meeting.mp4

# 出力ファイル名を指定
python main.py meeting.mp4 -o my_transcript.md
```

**出力例:**
```
meeting.mp4 → meeting_transcript.md
```

### 2. Web版

#### uv使用
```bash
# Streamlit Web版を起動
uv run streamlit run web_app.py
```

#### pip使用
```bash
# Streamlit Web版を起動
streamlit run web_app.py
```

ブラウザで http://localhost:8501 を開いて、ファイルをアップロード！

## 📊 出力例

生成されるMarkdownファイルの例：

```markdown
# 🎵 音声文字起こし結果

**📁 入力ファイル**: meeting.mp4
**📅 処理日時**: 2025年1月30日 14:30:15
**👥 話者数**: 2名
**📊 総セグメント数**: 15個

---

## 📝 発話内容

**[00:00:05 - 00:00:12] SPEAKER_00:**
> こんにちは、今日はお忙しい中ありがとうございます

**[00:00:13 - 00:00:20] SPEAKER_01:**
> こちらこそよろしくお願いします
```

## 🎯 対応ファイル形式

| 種類 | 対応形式 |
|------|----------|
| 動画 | MP4, AVI, MOV, MKV, WebM |
| 音声 | WAV, MP3, M4A, FLAC |

## ⚙️ 技術仕様

- **話者分離**: pyannote/speaker-diarization-3.1
- **文字起こし**: OpenAI Whisper Large V3
- **音声抽出**: MoviePy
- **対応言語**: 日本語（メイン）

## 💡 使用シーン

- 📋 **会議録**: Zoom/Teams録画から議事録生成
- 🎓 **講義録**: 授業・セミナーの自動文字起こし
- 🎤 **インタビュー**: 対談・インタビューの文字起こし
- 📺 **動画コンテンツ**: YouTube動画の字幕作成

## 🤖 LLM連携で議事録自動生成

### Step 1: 文字起こし実行

#### uv使用
```bash
uv run python main.py meeting.mp4
# または
uv run transcribe meeting.mp4
```

#### pip使用
```bash
python main.py meeting.mp4
```

### Step 2: LLMで後処理
生成されたMarkdownをChatGPT/Claudeに送信：

```
以下の文字起こし結果から議事録を作成してください：
- 誤字脱字を修正
- 適切な句読点を追加  
- 重要なポイントを箇条書きで整理
- アクションアイテムを抽出

[文字起こし結果をここに貼り付け]
```

### 完全自動化フロー
```
MP4動画 → 音声抽出 → 話者分離 → 文字起こし → LLM処理 → 完璧な議事録
```

## 🛠 トラブルシューティング

### よくある問題

**Q: uvのインストールエラー**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# pipでuvをインストール
pip install uv
```

**Q: "torch" や "transformers" のインストールエラー**

#### uv使用
```bash
# 自動的に適切なバージョンがインストールされます
uv sync
```

#### pip使用
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

**Q: "moviepy" のエラー**

#### uv使用
```bash
# pyproject.tomlに既に含まれているので、同期するだけ
uv sync
```

#### pip使用
```bash
pip install moviepy
```

**Q: GPU関連エラー**
- CPUでも動作します（GPUより少し時間がかかります）
- CUDAが使用可能な場合は自動的にGPUを使用します

**Q: 音声が検出されない**
- 音声トラックが含まれているか確認
- ファイルが破損していないか確認

## 🎁 カスタマイズ

### より軽量なモデルを使用
`audio_transcriber.py` の中で以下を変更：

```python
# Whisper Mediumを使用（軽量版）
self.whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-medium")
self.whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-medium")
```

### 話者数を固定
```python
# 話者数を3名に固定
diarization_result = self.diarization_pipeline(str(audio_path), num_speakers=3)
```

## 📝 ライセンス

個人利用・商用利用ともに自由です。使用するAIモデルの利用規約をご確認ください。

## ⚡ uvを使う利点

- **超高速**: pipより10-100倍高速なパッケージインストール
- **依存関係解決**: 複雑な依存関係も自動で適切に解決
- **仮想環境自動管理**: `.venv`フォルダを自動作成・管理
- **ロックファイル**: `uv.lock`で再現可能な環境を保証
- **クロスプラットフォーム**: Windows、macOS、Linux全対応

### uv vs pip 比較例

```bash
# pip（従来）
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
python main.py meeting.mp4

# uv（モダン）
uv run python main.py meeting.mp4  # これだけ！
```

---

**🎉 Happy transcribing!**

*MP4動画を投げ込むだけで議事録完成の魔法をお楽しみください✨*