import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from pyannote.audio import Pipeline, Audio
from pyannote.core import Segment
from pathlib import Path
import warnings
import logging
from typing import Optional, List, Dict, Any
import datetime
import tempfile
import os

# 警告を抑制
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")

# moviepyのimport
try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logging.warning("moviepy is not installed. MP4 file support will be limited.")


class AudioProcessor:
    """音声・動画ファイルの話者分離と文字起こしを行うクラス"""
    
    def __init__(self):
        self.device = self._setup_device()
        self.pipeline = None
        self.processor = None
        self.model = None
        self.audio_handler = None
        self.temp_audio_file = None
        
    def _setup_device(self) -> torch.device:
        """最適なデバイスを自動選択"""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")
    
    def _load_models(self):
        """モデルを読み込み"""
        logging.info("モデルを読み込み中...")
        
        # 話者分離モデル
        self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        self.pipeline.to(self.device)
        
        # 文字起こしモデル
        self.processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")
        self.model = WhisperForConditionalGeneration.from_pretrained(
            "openai/whisper-large-v3",
            torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
        ).to(self.device)
        self.model.eval()
        
        # 音声ハンドラ
        self.audio_handler = Audio(sample_rate=16000, mono=True)
        
        logging.info("モデル読み込み完了")
    
    def extract_audio_from_video(self, video_path: Path) -> Optional[Path]:
        """動画から音声を抽出"""
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError("moviepy が必要です: pip install moviepy")
        
        try:
            logging.info(f"動画から音声を抽出中: {video_path}")
            
            # 一時ファイル作成
            temp_fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='audio_')
            os.close(temp_fd)
            temp_audio_path = Path(temp_path)
            
            # 音声抽出
            with VideoFileClip(str(video_path)) as video:
                if video.audio is None:
                    raise RuntimeError("動画に音声トラックがありません")
                
                video.audio.write_audiofile(
                    str(temp_audio_path),
                    codec='pcm_s16le',
                    verbose=False,
                    logger=None
                )
            
            self.temp_audio_file = temp_audio_path
            logging.info("音声抽出完了")
            return temp_audio_path
            
        except Exception as e:
            logging.error(f"音声抽出エラー: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    
    def process_file(self, input_path: Path) -> List[Dict[str, Any]]:
        """ファイルを処理して話者分離と文字起こしを実行"""
        
        # モデル読み込み（初回のみ）
        if self.pipeline is None:
            self._load_models()
        
        # 音声ファイルの準備
        if input_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
            audio_path = self.extract_audio_from_video(input_path)
            if audio_path is None:
                raise RuntimeError("音声抽出に失敗しました")
        else:
            audio_path = input_path
        
        # 話者分離
        logging.info("話者分離を実行中...")
        diarization = self.pipeline(str(audio_path))
        
        # 各セグメントの文字起こし
        logging.info("文字起こしを実行中...")
        results = []
        
        for segment, _, speaker in diarization.itertracks(yield_label=True):
            try:
                # 音声セグメントを取得
                waveform, sample_rate = self.audio_handler.crop(str(audio_path), segment)
                
                # セグメントが短すぎる場合はスキップ
                if waveform.shape[-1] / sample_rate < 0.1:
                    continue
                
                # 文字起こし
                text = self._transcribe_segment(waveform, sample_rate)
                
                if text and text.strip():
                    results.append({
                        'start': self._format_time(segment.start),
                        'end': self._format_time(segment.end),
                        'speaker': speaker,
                        'text': text.strip()
                    })
                    
            except Exception as e:
                logging.warning(f"セグメント処理エラー: {e}")
                continue
        
        logging.info(f"処理完了: {len(results)}個のセグメント")
        return results
    
    def _transcribe_segment(self, waveform: torch.Tensor, sample_rate: int) -> Optional[str]:
        """音声セグメントを文字起こし"""
        try:
            # 波形をnumpy配列に変換
            if waveform.ndim == 2:
                waveform_np = waveform.squeeze(0).numpy().astype("float32")
            else:
                waveform_np = waveform.numpy().astype("float32")
            
            # Whisperで処理
            input_features = self.processor(
                waveform_np, 
                sampling_rate=sample_rate, 
                return_tensors="pt"
            ).input_features.to(self.device)
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_features,
                    forced_decoder_ids=self.processor.get_decoder_prompt_ids(
                        language="ja", task="transcribe"
                    )
                )
            
            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return text
            
        except Exception as e:
            logging.warning(f"文字起こしエラー: {e}")
            return None
    
    def _format_time(self, seconds: float) -> str:
        """秒を HH:MM:SS 形式に変換"""
        total_seconds = int(seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def results_to_markdown(self, results: List[Dict[str, Any]], input_filename: str) -> str:
        """結果をMarkdown形式に変換"""
        
        markdown_lines = [
            "# 音声文字起こし結果",
            "",
            f"**入力ファイル**: {input_filename}",
            f"**処理日時**: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"**話者数**: {len(set(r['speaker'] for r in results))}名",
            f"**総セグメント数**: {len(results)}個",
            "",
            "## 発話内容",
            ""
        ]
        
        for result in results:
            markdown_lines.extend([
                f"**[{result['start']} - {result['end']}] {result['speaker']}:**",
                result['text'],
                ""
            ])
        
        return "\n".join(markdown_lines)
    
    def cleanup(self):
        """一時ファイルのクリーンアップ"""
        if self.temp_audio_file and self.temp_audio_file.exists():
            try:
                os.unlink(self.temp_audio_file)
                self.temp_audio_file = None
                logging.info("一時ファイルを削除しました")
            except Exception as e:
                logging.warning(f"一時ファイル削除エラー: {e}")
    
    def __del__(self):
        self.cleanup()