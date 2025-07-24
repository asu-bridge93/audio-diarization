import streamlit as st
import tempfile
from pathlib import Path
import logging
import warnings
from audio_processor import AudioProcessor

# 警告を抑制
warnings.filterwarnings("ignore", category=UserWarning)

# ページ設定
st.set_page_config(
    page_title="音声文字起こしツール",
    page_icon="🎵",
    layout="wide"
)

# ログ設定
logging.basicConfig(level=logging.INFO)

# セッション状態の初期化
if 'processor' not in st.session_state:
    st.session_state.processor = AudioProcessor()

def main():
    st.title("🎵 音声文字起こしツール")
    st.markdown("動画・音声ファイルから**話者分離付きの文字起こし**を自動生成します")
    
    # moviepyの状態チェック
    try:
        from moviepy.editor import VideoFileClip
        moviepy_available = True
    except ImportError:
        moviepy_available = False
        st.warning("⚠️ MoviePyがインストールされていません。動画ファイル（MP4等）の処理ができません。")
        st.code("uv pip install moviepy", language="bash")
    
    # サイドバー
    with st.sidebar:
        st.header("📋 使い方")
        if moviepy_available:
            st.markdown("""
            1. 動画または音声ファイルをアップロード
            2. 処理開始ボタンをクリック
            3. 結果をダウンロード
            
            **対応形式:**
            - 動画: MP4, AVI, MOV, MKV, WebM
            - 音声: WAV, MP3, M4A, FLAC
            """)
        else:
            st.markdown("""
            1. 音声ファイルをアップロード
            2. 処理開始ボタンをクリック
            3. 結果をダウンロード
            
            **対応形式:**
            - 音声: WAV, MP3, M4A, FLAC
            
            ⚠️ 動画対応にはMoviePyが必要です
            """)
        
        st.header("⚙️ 技術仕様")
        st.markdown("""
        - **話者分離**: pyannote/speaker-diarization-3.1
        - **文字起こし**: Whisper Large V3
        - **言語**: 日本語
        """)
    
    # メインコンテンツ
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📁 ファイルアップロード")
        
        # ファイルサイズに関する注意書き
        st.info("💡 **大きなファイル（500MB以上）の場合はコマンドライン版の使用をお勧めします**")
        
        with st.expander("📋 大きなファイルの処理方法", expanded=False):
            st.markdown("""
            **コマンドライン版の使用方法:**
            
            1. ファイルをプロジェクトフォルダに配置
            2. ターミナルで以下を実行:
            ```bash
            uv run python main.py 研究MTG0724.mp4
            ```
            3. 処理完了後、`.md`ファイルが生成されます
            
            **利点:**
            - ファイルサイズ制限なし
            - メモリ効率が良い
            - 処理速度が速い
            """)
        
        # moviepyの状態に応じて対応形式を決定
        try:
            from moviepy.editor import VideoFileClip
            file_types = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'wav', 'mp3', 'm4a', 'flac']
            help_text = "動画・音声ファイル対応（最大: 2GB）"
        except ImportError:
            file_types = ['wav', 'mp3', 'm4a', 'flac']
            help_text = "音声ファイルのみ対応（MoviePyインストールで動画対応可能）"
        
        uploaded_file = st.file_uploader(
            "動画または音声ファイルを選択してください",
            type=file_types,
            help=help_text
        )
        
        if uploaded_file is not None:
            # ファイル情報表示
            file_size_mb = len(uploaded_file.read()) / (1024*1024)
            uploaded_file.seek(0)  # ファイルポインタをリセット
            
            st.success(f"✅ ファイルがアップロードされました: {uploaded_file.name}")
            st.info(f"📊 ファイルサイズ: {file_size_mb:.1f} MB")
            
            # 大きなファイルに対する警告
            if file_size_mb > 500:
                st.warning("⚠️ ファイルが大きいため、処理に時間がかかる可能性があります。コマンドライン版の使用をお勧めします。")
            elif file_size_mb > 1000:
                st.error("❌ ファイルが非常に大きいです。コマンドライン版をご利用ください。")
                st.stop()
            
            # 処理開始ボタン
            if st.button("🚀 文字起こしを開始", type="primary", use_container_width=True):
                try:
                    process_file(uploaded_file)
                except Exception as e:
                    if "413" in str(e) or "Payload Too Large" in str(e):
                        st.error("❌ ファイルサイズが制限を超えています。コマンドライン版をご利用ください:")
                        st.code(f"uv run python main.py {uploaded_file.name}")
                    else:
                        st.error(f"❌ エラーが発生しました: {str(e)}")
                        logging.error(f"処理エラー: {e}")
    
    with col2:
        st.header("📄 処理結果")
        
        # 結果表示エリア
        if 'markdown_result' in st.session_state:
            st.markdown("### プレビュー")
            st.markdown(st.session_state.markdown_result)
            
            # ダウンロードボタン
            st.download_button(
                label="📥 Markdownファイルをダウンロード",
                data=st.session_state.markdown_result,
                file_name=f"{Path(st.session_state.original_filename).stem}_transcript.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.info("左側でファイルをアップロードして処理を開始してください")


def process_file(uploaded_file):
    """アップロードされたファイルを処理"""
    
    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 一時ファイルに保存
        status_text.text("📁 ファイルを準備中...")
        progress_bar.progress(10)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = Path(tmp_file.name)
        
        # モデル読み込み確認
        status_text.text("🤖 モデルを準備中...")
        progress_bar.progress(30)
        
        # 処理実行
        status_text.text("🎵 音声を解析中...")
        progress_bar.progress(50)
        
        results = st.session_state.processor.process_file(tmp_path)
        
        if not results:
            st.error("❌ 文字起こし結果が得られませんでした")
            return
        
        status_text.text("📝 結果を生成中...")
        progress_bar.progress(80)
        
        # Markdown生成
        markdown_content = st.session_state.processor.results_to_markdown(
            results, uploaded_file.name
        )
        
        # セッション状態に保存
        st.session_state.markdown_result = markdown_content
        st.session_state.original_filename = uploaded_file.name
        
        status_text.text("✅ 処理完了！")
        progress_bar.progress(100)
        
        # 成功メッセージ
        st.success(f"🎉 {len(results)}個のセグメントを処理しました！")
        
        # 一時ファイル削除
        tmp_path.unlink()
        
    except Exception as e:
        st.error(f"❌ エラーが発生しました: {str(e)}")
        logging.error(f"処理エラー: {e}")
        
        # 一時ファイルが残っている場合は削除
        if 'tmp_path' in locals() and tmp_path.exists():
            tmp_path.unlink()
    
    finally:
        # プログレスバーをクリア
        progress_bar.empty()
        status_text.empty()


# LLM連携の提案
def show_llm_integration():
    with st.expander("🤖 LLMを使った議事録生成", expanded=False):
        st.markdown("""
        文字起こし結果をChatGPTやClaudeに送って、さらに高品質な議事録を生成できます：
        
        **プロンプト例:**
        ```
        以下の文字起こし結果から議事録を作成してください：
        - 誤字脱字を修正
        - 適切な句読点を追加
        - 重要なポイントを箇条書きで整理
        - アクションアイテムがあれば抽出
        
        [ここに文字起こし結果を貼り付け]
        ```
        """)


if __name__ == "__main__":
    main()
    show_llm_integration()