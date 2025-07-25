"""
音声文字起こし処理のコアクラス
MP4動画から音声抽出 → 話者分離 → 文字起こし → Markdown出力
"""

import torch
import warnings
import logging
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 外部ライブラリ
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from pyannote.audio import Pipeline, Audio
from moviepy.editor import VideoFileClip

# 警告を抑制
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class AudioTranscriber:
    """MP4動画から話者分離付き文字起こしを行うクラス"""
    
    def __init__(self):
        """初期化"""
        self.device = self._get_device()
        self.diarization_pipeline = None
        self.whisper_processor = None
        self.whisper_model = None
        self.audio_handler = None
        
        logging.info(f"使用デバイス: {self.device}")
    
    def _get_device(self) -> torch.device:
        """最適な処理デバイスを自動選択"""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    
    def _load_models(self):
        """必要なAIモデルを読み込み"""
        if self.diarization_pipeline is not None:
            return  # 既に読み込み済み
        
        logging.info("AIモデルを読み込み中...")
        
        # 話者分離モデル
        self.diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        self.diarization_pipeline.to(self.device)
        
        # Whisper文字起こしモデル
        self.whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")
        self.whisper_model = WhisperForConditionalGeneration.from_pretrained(
            "openai/whisper-large-v3",
            torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
        ).to(self.device)
        self.whisper_model.eval()
        
        # 音声処理ハンドラ
        self.audio_handler = Audio(sample_rate=16000, mono=True)
        
        logging.info("モデル読み込み完了")
    
    def extract_audio_from_mp4(self, mp4_path: Path) -> Path:
        """MP4動画から音声を抽出してWAVファイルを作成"""
        logging.info(f"MP4から音声抽出中: {mp4_path.name}")
        
        # 一時音声ファイルパス
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='extracted_audio_')
        os.close(temp_fd)
        temp_audio_path = Path(temp_path)
        
        try:
            # MoviePyで音声抽出
            with VideoFileClip(str(mp4_path)) as video:
                if video.audio is None:
                    raise ValueError("MP4ファイルに音声トラックがありません")
                
                video.audio.write_audiofile(
                    str(temp_audio_path),
                    codec='pcm_s16le',
                    verbose=False,
                    logger=None
                )
            
            logging.info("音声抽出完了")
            return temp_audio_path
            
        except Exception as e:
            if temp_audio_path.exists():
                temp_audio_path.unlink()
            raise RuntimeError(f"音声抽出失敗: {e}")
    
    def transcribe_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        ファイルを処理して話者分離と文字起こしを実行
        
        Args:
            file_path: MP4動画ファイルまたは音声ファイルのパス
            
        Returns:
            話者分離結果のリスト [{'start': '00:00:05', 'end': '00:00:12', 'speaker': 'SPEAKER_00', 'text': '...'}]
        """
        # モデル読み込み
        self._load_models()
        
        # ファイル形式に応じて音声ファイルを準備
        if file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            audio_path = self.extract_audio_from_mp4(file_path)
            temp_file = audio_path
        else:
            audio_path = file_path
            temp_file = None
        
        try:
            # 話者分離実行
            logging.info("話者分離を実行中...")
            diarization_result = self.diarization_pipeline(str(audio_path))
            
            # 各話者セグメントを文字起こし
            logging.info("文字起こしを実行中...")
            transcription_results = []
            
            for segment, _, speaker_label in diarization_result.itertracks(yield_label=True):
                # 短すぎるセグメントはスキップ
                if segment.duration < 0.5:
                    continue
                
                # 音声セグメントを取得
                waveform, sample_rate = self.audio_handler.crop(str(audio_path), segment)
                
                # 文字起こし実行
                transcribed_text = self._transcribe_audio_segment(waveform, sample_rate)
                
                if transcribed_text and transcribed_text.strip():
                    transcription_results.append({
                        'start': self._seconds_to_timestamp(segment.start),
                        'end': self._seconds_to_timestamp(segment.end),
                        'speaker': speaker_label,
                        'text': transcribed_text.strip()
                    })
            
            logging.info(f"処理完了: {len(transcription_results)}個のセグメント")
            return transcription_results
            
        finally:
            # 一時ファイルの削除
            if temp_file and temp_file.exists():
                temp_file.unlink()
    
    def _transcribe_audio_segment(self, waveform: torch.Tensor, sample_rate: int) -> Optional[str]:
        """音声セグメントをWhisperで文字起こし"""
        try:
            # Torch TensorをNumPy配列に変換
            if waveform.ndim == 2:
                audio_array = waveform.squeeze(0).numpy()
            else:
                audio_array = waveform.numpy()
            
            # Whisperで処理
            input_features = self.whisper_processor(
                audio_array,
                sampling_rate=sample_rate,
                return_tensors="pt"
            ).input_features.to(self.device)
            
            # 日本語文字起こし実行
            with torch.no_grad():
                generated_ids = self.whisper_model.generate(
                    input_features,
                    forced_decoder_ids=self.whisper_processor.get_decoder_prompt_ids(
                        language="ja", task="transcribe"
                    )
                )
            
            # テキストに変換
            transcribed_text = self.whisper_processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
            
            return transcribed_text
            
        except Exception as e:
            logging.warning(f"セグメント文字起こしエラー: {e}")
            return None
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """秒数をHH:MM:SS形式のタイムスタンプに変換"""
        total_seconds = int(seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def create_markdown_report(self, results: List[Dict[str, Any]], input_filename: str) -> str:
        """
        文字起こし結果をMarkdown形式のレポートとして生成
        
        Args:
            results: transcribe_file()の戻り値
            input_filename: 入力ファイル名
            
        Returns:
            Markdown形式の文字起こしレポート
        """
        # ヘッダー情報
        markdown_lines = [
            "# 🎵 音声文字起こし結果",
            "",
            f"**📁 入力ファイル**: {input_filename}",
            f"**📅 処理日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"**👥 話者数**: {len(set(r['speaker'] for r in results))}名",
            f"**📊 総セグメント数**: {len(results)}個",
            "",
            "---",
            "",
            "## 📝 発話内容",
            ""
        ]
        
        # 各セグメントの内容
        for result in results:
            markdown_lines.extend([
                f"**[{result['start']} - {result['end']}] {result['speaker']}:**",
                f"> {result['text']}",
                ""
            ])
        
        return "\n".join(markdown_lines)
    
    def save_markdown_file(self, markdown_content: str, output_path: Path):
        """Markdownファイルとして保存"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logging.info(f"結果を保存しました: {output_path}")