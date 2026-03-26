"""
video_creator.py
================
AI 생성 스크립트를 기반으로 TTS 오디오 + 이미지 슬라이드쇼 영상을 생성하는 모듈.

OpenAI TTS API를 사용하여 내레이션 오디오를 생성하고,
DALL-E 또는 기본 이미지와 결합하여 업로드 가능한 MP4 영상을 만듭니다.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

from config_loader import get_openai_api_key, load_channel_config


class VideoCreator:
    """AI 기반 영상 생성기."""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.config = load_channel_config(channel_id)
        self.client = OpenAI(api_key=get_openai_api_key())
        self.language = self.config["language"]

    def generate_tts_audio(self, script: str, output_path: str, voice: str = None) -> str:
        """
        OpenAI TTS API로 내레이션 오디오를 생성합니다.

        Args:
            script: 내레이션 스크립트 텍스트
            output_path: 오디오 파일 저장 경로
            voice: TTS 음성 (alloy, echo, fable, onyx, nova, shimmer)

        Returns:
            생성된 오디오 파일 경로
        """
        if voice is None:
            voice = "nova" if self.language == "ko" else "onyx"

        print(f"[INFO] TTS 오디오 생성 중 (음성: {voice})...")

        # 스크립트가 너무 길면 분할
        max_chars = 4096
        if len(script) > max_chars:
            script = script[:max_chars]
            print(f"[WARNING] 스크립트가 {max_chars}자로 잘렸습니다.")

        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=script,
            response_format="mp3"
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(output_path)
        print(f"[INFO] TTS 오디오 저장 완료: {output_path}")
        return output_path

    def create_title_card(self, title: str, output_path: str, size: tuple = (1920, 1080)) -> str:
        """
        제목 카드 이미지를 생성합니다.

        Args:
            title: 영상 제목
            output_path: 이미지 저장 경로
            size: 이미지 크기 (width, height)

        Returns:
            생성된 이미지 파일 경로
        """
        img = Image.new("RGB", size, color="#1a1a2e")
        draw = ImageDraw.Draw(img)

        # 폰트 설정 (시스템 기본 폰트 사용)
        try:
            font_size = 60
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()

        # 텍스트 줄바꿈 처리
        max_width = size[0] - 200
        words = title.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # 텍스트 중앙 배치
        total_height = len(lines) * 80
        y_start = (size[1] - total_height) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (size[0] - text_width) // 2
            y = y_start + i * 80

            # 그림자 효과
            draw.text((x + 3, y + 3), line, fill="#000000", font=font)
            draw.text((x, y), line, fill="#ffffff", font=font)

        # 채널명 하단 표시
        channel_name = self.config["channel_name"]
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except (IOError, OSError):
            small_font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), channel_name, font=small_font)
        cw = bbox[2] - bbox[0]
        draw.text(((size[0] - cw) // 2, size[1] - 100), channel_name, fill="#e94560", font=small_font)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")
        print(f"[INFO] 제목 카드 생성 완료: {output_path}")
        return output_path

    def create_video_from_audio_and_image(
        self,
        audio_path: str,
        image_path: str,
        output_path: str
    ) -> str:
        """
        오디오와 이미지를 결합하여 MP4 영상을 생성합니다.
        ffmpeg를 사용합니다.

        Args:
            audio_path: 오디오 파일 경로
            image_path: 배경 이미지 경로
            output_path: 출력 영상 경로

        Returns:
            생성된 영상 파일 경로
        """
        print(f"[INFO] 영상 생성 중 (ffmpeg)...")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[ERROR] ffmpeg 실패: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"ffmpeg 오류: {result.stderr}")

        print(f"[INFO] 영상 생성 완료: {output_path}")
        return output_path

    def create_full_video(self, content: dict, output_dir: str = None) -> dict:
        """
        콘텐츠 딕셔너리를 기반으로 전체 영상 제작 파이프라인을 실행합니다.

        Args:
            content: content_generator가 생성한 콘텐츠 딕셔너리
            output_dir: 출력 디렉토리

        Returns:
            생성된 파일 경로들을 담은 딕셔너리
        """
        if output_dir is None:
            output_dir = str(Path(__file__).resolve().parent.parent / "assets" / "output")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = f"{self.channel_id}_{timestamp}"

        paths = {}

        # 1. 제목 카드 생성
        title_card_path = os.path.join(output_dir, f"{prefix}_title.png")
        self.create_title_card(content["title"], title_card_path)
        paths["title_card"] = title_card_path

        # 2. TTS 오디오 생성
        audio_path = os.path.join(output_dir, f"{prefix}_audio.mp3")
        self.generate_tts_audio(content["script"], audio_path)
        paths["audio"] = audio_path

        # 3. 영상 합성
        video_path = os.path.join(output_dir, f"{prefix}_video.mp4")
        self.create_video_from_audio_and_image(audio_path, title_card_path, video_path)
        paths["video"] = video_path

        print(f"\n[INFO] 전체 영상 제작 완료:")
        for key, path in paths.items():
            size = os.path.getsize(path) / (1024 * 1024)
            print(f"  {key}: {path} ({size:.1f} MB)")

        return paths


def main():
    """CLI 진입점."""
    import argparse

    parser = argparse.ArgumentParser(description="AI 영상 생성 도구")
    parser.add_argument(
        "channel",
        choices=["mydachshundtrio", "drpangpsych"],
        help="대상 채널 ID"
    )
    parser.add_argument(
        "--content-file",
        type=str,
        required=True,
        help="콘텐츠 JSON 파일 경로"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 디렉토리"
    )

    args = parser.parse_args()

    # 콘텐츠 로드
    with open(args.content_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    creator = VideoCreator(args.channel)
    paths = creator.create_full_video(content, output_dir=args.output_dir)

    # GitHub Actions 출력 변수 설정
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"video_path={paths.get('video', '')}\n")
            f.write(f"thumbnail_path={paths.get('title_card', '')}\n")

    print(f"\n영상 파일: {paths.get('video')}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
