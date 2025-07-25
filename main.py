#!/usr/bin/env python3
"""
音声文字起こしツール - コマンドライン版
使用例: python main.py meeting.mp4
"""

import sys
import argparse
from pathlib import Path
import logging

from audio_transcriber import AudioTranscriber


def main():
    """メイン処理"""
    # コマンドライン引数解析
    parser = argparse.ArgumentParser(
        description="MP4動画から話者分離付き文字起こしを実行"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="入力ファイルパス（MP4動画または音声ファイル）"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="出力ファイルパス（指定しない場合は自動生成）"
    )
    
    args = parser.parse_args()
    
    # 入力ファイルの存在確認
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ エラー: ファイルが見つかりません: {input_path}")
        sys.exit(1)
    
    # 対応ファイル形式の確認
    supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.wav', '.mp3', '.m4a', '.flac']
    if input_path.suffix.lower() not in supported_formats:
        print(f"❌ エラー: 対応していないファイル形式です: {input_path.suffix}")
        print(f"対応形式: {', '.join(supported_formats)}")
        sys.exit(1)
    
    # 出力ファイルパスの決定
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_transcript.md"
    
    print("🎵 音声文字起こしツール")
    print("=" * 50)
    print(f"📁 入力ファイル: {input_path.name}")
    print(f"📄 出力ファイル: {output_path.name}")
    print()
    
    try:
        # 文字起こし処理実行
        transcriber = AudioTranscriber()
        
        print("🚀 処理を開始します...")
        results = transcriber.transcribe_file(input_path)
        
        if not results:
            print("❌ 文字起こし結果が得られませんでした")
            sys.exit(1)
        
        # Markdownレポート生成
        print("📝 レポートを生成中...")
        markdown_content = transcriber.create_markdown_report(results, input_path.name)
        
        # ファイル保存
        transcriber.save_markdown_file(markdown_content, output_path)
        
        # 結果表示
        print()
        print("✅ 処理完了！")
        print(f"👥 話者数: {len(set(r['speaker'] for r in results))}名")
        print(f"📊 セグメント数: {len(results)}個")
        print(f"📄 出力ファイル: {output_path}")
        
    except KeyboardInterrupt:
        print("\n⚠️ 処理が中断されました")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        logging.error(f"処理エラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()