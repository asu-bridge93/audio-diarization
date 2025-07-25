"""
音声文字起こしツール - Streamlit Web版
使用方法: streamlit run web_app.py
"""

import streamlit as st
import tempfile
from pathlib import Path
import logging

from audio_transcriber import AudioTranscriber


# ページ設定
st.set_page_config(
    page_title="🎵 音声文字起こしツール",
    page_icon="🎵",
    layout="wide"
)

# セッション状態の初期化
if 'transcriber' not in st.session_state:
    st.session_state.transcriber = AudioTranscriber()


def main():
    """メイン画面"""
    
    # タイトル
    st.title("🎵 音声文字起こしツール")
    st.markdown("MP4動画から**話者分離付きの文字起こし**を自動生成します")
    
    # サイドバー
    with st.sidebar:
        st.header("📋 使い方")
        st.markdown("""
        1. 動画または音声ファイルをアップロード
        2. 「文字起こし開始」ボタンをクリック
        3. 結果をダウンロード
        
        **対応形式:**
        - 動画: MP4, AVI, MOV, MKV, WebM
        - 音声: WAV, MP3, M4A, FLAC
        """)
        
        st.header("⚙️ 技術仕様")
        st.markdown("""
        - **話者分離**: pyannote/speaker-diarization-3.1
        - **文字起こし**: Whisper Large V3
        - **言語**: 日本語
        """)
    
    # メインエリア
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📁 ファイルアップロード")
        
        # ファイルアップローダー
        uploaded_file = st.file_uploader(
            "動画または音声ファイルを選択してください",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm', 'wav', 'mp3', 'm4a', 'flac'],
            help="最大サイズ: 2GB"
        )
        
        if uploaded_file is not None:
            # ファイル情報表示
            file_size_mb = len(uploaded_file.read()) / (1024*1024)
            uploaded_file.seek(0)  # ファイルポインタをリセット
            
            st.success(f"✅ ファイルがアップロードされました")
            st.info(f"📊 ファイル名: {uploaded_file.name}")
            st.info(f"📊 ファイルサイズ: {file_size_mb:.1f} MB")
            
            # 大きなファイルに対する警告
            if file_size_mb > 500:
                st.warning("⚠️ ファイルが大きいため、処理に時間がかかる可能性があります")
            
            # 処理開始ボタン
            if st.button("🚀 文字起こし開始", type="primary", use_container_width=True):
                process_uploaded_file(uploaded_file)
    
    with col2:
        st.header("📄 処理結果")
        
        # 結果表示エリア
        if 'markdown_result' in st.session_state:
            st.markdown("### プレビュー")
            
            # 結果の要約表示
            results = st.session_state.get('transcription_results', [])
            if results:
                st.success(f"✅ 処理完了！")
                
                col2a, col2b = st.columns(2)
                with col2a:
                    st.metric("話者数", f"{len(set(r['speaker'] for r in results))}名")
                with col2b:
                    st.metric("セグメント数", f"{len(results)}個")
            
            # Markdown表示
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
    
    # LLM連携の提案
    with st.expander("🤖 LLMを使った議事録生成のコツ", expanded=False):
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


def process_uploaded_file(uploaded_file):
    """アップロードされたファイルを処理"""
    
    # プログレスバー
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 一時ファイルに保存
        status_text.text("📁 ファイルを準備中...")
        progress_bar.progress(20)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = Path(tmp_file.name)
        
        # 文字起こし処理
        status_text.text("🤖 AIモデルを準備中...")
        progress_bar.progress(40)
        
        status_text.text("🎵 音声解析中...")
        progress_bar.progress(60)
        
        # 処理実行
        results = st.session_state.transcriber.transcribe_file(tmp_path)
        
        if not results:
            st.error("❌ 文字起こし結果が得られませんでした")
            return
        
        status_text.text("📝 レポート生成中...")
        progress_bar.progress(80)
        
        # Markdownレポート生成
        markdown_content = st.session_state.transcriber.create_markdown_report(
            results, uploaded_file.name
        )
        
        # セッション状態に保存
        st.session_state.transcription_results = results
        st.session_state.markdown_result = markdown_content
        st.session_state.original_filename = uploaded_file.name
        
        status_text.text("✅ 処理完了！")
        progress_bar.progress(100)
        
        # 成功メッセージ
        st.balloons()
        
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


if __name__ == "__main__":
    main()