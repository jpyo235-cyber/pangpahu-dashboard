"""
pipeline.py
===========
전체 자동화 파이프라인 오케스트레이터.

콘텐츠 생성 → 영상 제작 → YouTube 업로드의 전체 흐름을 관리합니다.
GitHub Actions에서 호출되는 메인 진입점입니다.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 스크립트 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_channel_config, PROJECT_ROOT
from content_generator import ContentGenerator
from video_creator import VideoCreator
from youtube_uploader import YouTubeUploader


class Pipeline:
    """자동화 파이프라인 관리자."""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.config = load_channel_config(channel_id)
        self.output_dir = str(PROJECT_ROOT / "assets" / "output" / channel_id)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def run(
        self,
        content_type: str = "script",
        custom_topic: str = None,
        privacy_status: str = "private",
        skip_upload: bool = False,
        skip_video: bool = False
    ) -> dict:
        """
        전체 파이프라인을 실행합니다.

        Args:
            content_type: 'script' 또는 'shorts'
            custom_topic: 사용자 지정 주제
            privacy_status: YouTube 공개 상태
            skip_upload: 업로드 건너뛰기 (테스트용)
            skip_video: 영상 생성 건너뛰기 (콘텐츠만 생성)

        Returns:
            파이프라인 실행 결과 딕셔너리
        """
        result = {
            "channel_id": self.channel_id,
            "channel_name": self.config["channel_name"],
            "started_at": datetime.utcnow().isoformat(),
            "steps": {}
        }

        try:
            # ── Step 1: 콘텐츠 생성 ──
            print(f"\n{'='*60}")
            print(f"[STEP 1/3] AI 콘텐츠 생성")
            print(f"{'='*60}")

            generator = ContentGenerator(self.channel_id)
            content = generator.generate_video_content(
                content_type=content_type,
                custom_topic=custom_topic
            )
            content_file = generator.save_content(content, output_dir=self.output_dir)

            result["steps"]["content_generation"] = {
                "status": "success",
                "title": content["title"],
                "content_file": content_file
            }

            if skip_video:
                print("[INFO] 영상 생성 건너뛰기 (skip_video=True)")
                result["steps"]["video_creation"] = {"status": "skipped"}
                result["steps"]["upload"] = {"status": "skipped"}
                result["status"] = "completed_content_only"
                return result

            # ── Step 2: 영상 제작 ──
            print(f"\n{'='*60}")
            print(f"[STEP 2/3] 영상 제작 (TTS + 이미지)")
            print(f"{'='*60}")

            creator = VideoCreator(self.channel_id)
            paths = creator.create_full_video(content, output_dir=self.output_dir)

            result["steps"]["video_creation"] = {
                "status": "success",
                "video_path": paths.get("video"),
                "thumbnail_path": paths.get("title_card")
            }

            if skip_upload:
                print("[INFO] 업로드 건너뛰기 (skip_upload=True)")
                result["steps"]["upload"] = {"status": "skipped"}
                result["status"] = "completed_no_upload"
                return result

            # ── Step 3: YouTube 업로드 ──
            print(f"\n{'='*60}")
            print(f"[STEP 3/3] YouTube 업로드")
            print(f"{'='*60}")

            uploader = YouTubeUploader(self.channel_id)
            upload_result = uploader.upload_from_content_file(
                content_file=content_file,
                video_path=paths["video"],
                privacy_status=privacy_status,
                thumbnail_path=paths.get("title_card")
            )

            result["steps"]["upload"] = {
                "status": upload_result.get("status", "unknown"),
                "video_id": upload_result.get("video_id"),
                "video_url": upload_result.get("video_url")
            }

            result["status"] = "success" if upload_result.get("status") == "uploaded" else "upload_failed"

        except Exception as e:
            print(f"\n[ERROR] 파이프라인 오류: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            result["status"] = "error"
            result["error"] = str(e)

        result["completed_at"] = datetime.utcnow().isoformat()

        # 실행 로그 저장
        log_file = os.path.join(
            self.output_dir,
            f"pipeline_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n[INFO] 파이프라인 로그 저장: {log_file}")

        return result


def main():
    """CLI 진입점 (GitHub Actions에서 호출)."""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube 자동화 파이프라인")
    parser.add_argument(
        "channel",
        choices=["mydachshundtrio", "drpangpsych"],
        help="대상 채널 ID"
    )
    parser.add_argument(
        "--type",
        choices=["script", "shorts"],
        default="script",
        help="콘텐츠 유형"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="사용자 지정 주제"
    )
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="공개 상태 (기본: private, 안전을 위해)"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="업로드 건너뛰기"
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="영상 생성 건너뛰기 (콘텐츠만 생성)"
    )

    args = parser.parse_args()

    print(f"\n{'#'*60}")
    print(f"# YouTube 자동화 파이프라인")
    print(f"# 채널: {args.channel}")
    print(f"# 시간: {datetime.utcnow().isoformat()}")
    print(f"{'#'*60}\n")

    pipeline = Pipeline(args.channel)
    result = pipeline.run(
        content_type=args.type,
        custom_topic=args.topic,
        privacy_status=args.privacy,
        skip_upload=args.skip_upload,
        skip_video=args.skip_video
    )

    # GitHub Actions 출력 변수 설정
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"pipeline_status={result.get('status', 'unknown')}\n")
            upload_step = result.get("steps", {}).get("upload", {})
            f.write(f"video_id={upload_step.get('video_id', '')}\n")
            f.write(f"video_url={upload_step.get('video_url', '')}\n")
            content_step = result.get("steps", {}).get("content_generation", {})
            f.write(f"video_title={content_step.get('title', '')}\n")

    # 최종 결과 출력
    print(f"\n{'='*60}")
    print(f"파이프라인 실행 결과: {result.get('status', 'unknown').upper()}")
    print(f"{'='*60}")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 실패 시 종료 코드 1
    if result.get("status") in ("error", "upload_failed"):
        sys.exit(1)


if __name__ == "__main__":
    main()
