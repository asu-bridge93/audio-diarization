# 🎵 音声文字起こしツール

動画・音声ファイルから**話者分離付きの文字起こし**を自動生成するシンプルなツールです。

## ✨ 特徴

- 🎬 **動画対応**: MP4から音声を自動抽出
- 👥 **話者分離**: 誰がいつ話したかを自動識別
- 📝 **日本語文字起こし**: 高精度なWhisper Large V3使用
- 🌐 **Webインターフェース**: ドラッグ&ドロップで簡単操作
- 🤖 **LLM連携**: 結果をそのまま議事録生成に活用

## 🚀 クイックスタート

### 1. インストール
```bash
pip install torch transformers pyannote.audio moviepy streamlit
```

### 2. 使用方法

#### コマンドライン版
```bash
python main.py meeting.mp4
# → meeting.md が生成されます
```

#### Web版（推奨）
```bash
streamlit run app.py
```
ブラウザで http://localhost:8501 を開いて、ファイルをアップロード！

## 📁 ファイル構成

```
├── audio_processor.py  # 🧠 AIモデル処理部分
├── main.py            # 💻 コマンドライン版
├── app.py             # 🌐 Streamlit Web版
└── README.md          # 📖 このファイル
```

## 📊 出力例

```markdown
# 音声文字起こし結果

**入力ファイル**: meeting.mp4
**処理日時**: 2025年1月30日 14:30:15
**話者数**: 2名
**総セグメント数**: 15個

## 発話内容

**[00:00:05 - 00:00:12] SPEAKER_00:**
こんにちは、今日はお忙しい中ありがとうございます

**[00:00:13 - 00:00:20] SPEAKER_01:**
こちらこそよろしくお願いします
```

## 🎯 対応ファイル形式

| 種類 | 対応形式 |
|------|----------|
| 動画 | MP4, AVI, MOV, MKV, WebM |
| 音声 | WAV, MP3, M4A, FLAC |

## 🤖 LLM連携で議事録自動生成

### Step 1: 文字起こし
```bash
python main.py meeting.mp4
# または Streamlit Web版を使用
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

## ⚙️ 技術仕様

- **話者分離**: pyannote/speaker-diarization-3.1
- **文字起こし**: OpenAI Whisper Large V3
- **音声抽出**: MoviePy
- **UI**: Streamlit
- **対応言語**: 日本語（メイン）

## 💡 使用シーン

- 📋 **会議録**: Zoom/Teams録画から議事録生成
- 🎓 **講義録**: 授業・セミナーの自動文字起こし
- 🎤 **インタビュー**: 対談・インタビューの文字起こし
- 📺 **動画コンテンツ**: YouTube動画の字幕作成

## 🛠 トラブルシューティング

### よくある問題

**Q: "moviepy is not installed" エラー**
```bash
pip install moviepy
```

**Q: GPU関連エラー**
```bash
# CPUでも動作します（少し時間がかかります）
```

**Q: 音声が検出されない**
- 音声トラックが含まれているか確認
- ファイルが破損していないか確認

## 🎁 おまけ機能

### カスタマイズ
`audio_processor.py` でモデルやパラメータを変更可能：

```python
# より軽量なモデルに変更
self.model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-medium")

# 話者数を固定
diarization = self.pipeline(str(audio_path), num_speakers=3)
```

## 📝 ライセンス

個人利用・商用利用ともに自由です。使用するAIモデルの利用規約をご確認ください。

---

**🎉 Happy transcribing!**

*会議動画を投げ込むだけで議事録完成の魔法をお楽しみください✨*