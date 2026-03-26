"""
youtube_uploader.py
===================
YouTube Data API v3를 사용한 영상 업로드 모듈.

이 모듈은 다음 기능을 제공합니다:
- 영상 파일 업로드 (resumable upload)
- 메타데이터 설정 (제목, 설명, 태그, 카테고리)
- 썸네일 업로드
- 업로드 상태 추적 및 재시도
"""

import json
import os
import sys
import time
import http.client
import httplib2
import random
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from youtube_auth import authenticate_headless, get_youtube_service
from config_loader import load_channel_config


# 재시도 설정
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)


class YouTubeUploader:
    """YouTube 영상 업로드 관리자."""

    def __init__(self, channel_id: str):
        """
        Args:
            channel_id: 'mydachshundtrio' 또는 'drpangpsych'
        """
        self.channel_id = channel_id
        self.config = load_channel_config(channel_id)

        # 인증
        print(f"[INFO] YouTube API 인증 중 - 채널: {self.config['channel_name']}")
        creds = authenticate_headless(channel_id)
        self.youtube = get_youtube_service(creds)
        print("[INFO] YouTube API 서비스 준비 완료")

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        category_id: str = None,
        privacy_status: str = "private",
        thumbnail_path: str = None,
        made_for_kids: bool = False
    ) -> dict:
        """
        YouTube에 영상을 업로드합니다.

        Args:
            video_path: 업로드할 영상 파일 경로
            title: 영상 제목
            description: 영상 설명
            tags: 태그 리스트
            category_id: YouTube 카테고리 ID
            privacy_status: 'private', 'unlisted', 또는 'public'
            thumbnail_path: 썸네일 이미지 경로 (선택)
            made_for_kids: 아동용 콘텐츠 여부

        Returns:
            업로드 결과 딕셔너리 (video_id 포함)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

        if category_id is None:
            category_id = self.config.get("category_id", "22")

        if tags is None:
            tags = self.config.get("default_tags", [])

        # 메타데이터 구성
        body = {
            "snippet": {
                "title": title[:100],  # YouTube 제목 제한
                "description": description[:5000],  # YouTube 설명 제한
                "tags": tags[:500],  # 태그 제한
                "categoryId": category_id,
                "defaultLanguage": self.config["language"],
                "defaultAudioLanguage": self.config["language"]
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids
            }
        }

        # 미디어 파일 준비
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024  # 1MB 청크
        )

        # 업로드 요청 생성
        print(f"[INFO] 업로드 시작 - 제목: {title}")
        print(f"[INFO] 파일: {video_path}")
        print(f"[INFO] 공개 상태: {privacy_status}")

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        # Resumable upload 실행
        response = self._resumable_upload(request)

        if response:
            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"[SUCCESS] 업로드 완료!")
            print(f"  Video ID: {video_id}")
            print(f"  URL: {video_url}")

            # 썸네일 업로드
            if thumbnail_path and os.path.exists(thumbnail_path):
                self._upload_thumbnail(video_id, thumbnail_path)

            return {
                "video_id": video_id,
                "video_url": video_url,
                "title": title,
                "status": "uploaded",
                "privacy_status": privacy_status
            }
        else:
            return {"status": "failed", "title": title}

    def _resumable_upload(self, request) -> dict:
        """
        Resumable upload를 실행합니다. 실패 시 지수 백오프로 재시도합니다.

        Args:
            request: YouTube API 업로드 요청 객체

        Returns:
            업로드 응답 딕셔너리
        """
        response = None
        error = None
        retry = 0

        while response is None:
            try:
                print(f"[INFO] 업로드 진행 중...")
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"[INFO] 업로드 진행률: {progress}%")
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"HTTP 오류 {e.resp.status}: {e.content.decode()}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = str(e)

            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    print(f"[ERROR] 최대 재시도 횟수 초과", file=sys.stderr)
                    return None

                wait_time = random.random() * (2 ** retry)
                print(f"[WARNING] {error} - {wait_time:.1f}초 후 재시도 ({retry}/{MAX_RETRIES})")
                time.sleep(wait_time)
                error = None

        return response

    def _upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """
        영상 썸네일을 업로드합니다.

        Args:
            video_id: YouTube 영상 ID
            thumbnail_path: 썸네일 이미지 파일 경로
        """
        try:
            print(f"[INFO] 썸네일 업로드 중: {thumbnail_path}")
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png")
            ).execute()
            print("[INFO] 썸네일 업로드 완료")
        except HttpError as e:
            print(f"[WARNING] 썸네일 업로드 실패 (영상 업로드는 성공): {e}", file=sys.stderr)

    def upload_from_content_file(
        self,
        content_file: str,
        video_path: str,
        privacy_status: str = "private",
        thumbnail_path: str = None
    ) -> dict:
        """
        콘텐츠 생성기가 만든 JSON 파일의 메타데이터를 사용하여 업로드합니다.

        Args:
            content_file: content_generator가 생성한 JSON 파일 경로
            video_path: 업로드할 영상 파일 경로
            privacy_status: 공개 상태
            thumbnail_path: 썸네일 경로

        Returns:
            업로드 결과 딕셔너리
        """
        with open(content_file, "r", encoding="utf-8") as f:
            content = json.load(f)

        return self.upload_video(
            video_path=video_path,
            title=content["title"],
            description=content["description"],
            tags=content.get("tags", []),
            category_id=content.get("metadata", {}).get("category_id"),
            privacy_status=privacy_status,
            thumbnail_path=thumbnail_path
        )


def main():
    """CLI 진입점."""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube 영상 업로드 도구")
    parser.add_argument(
        "channel",
        choices=["mydachshundtrio", "drpangpsych"],
        help="대상 채널 ID"
    )
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="업로드할 영상 파일 경로"
    )
    parser.add_argument(
        "--content-file",
        type=str,
        default=None,
        help="콘텐츠 JSON 파일 경로 (메타데이터 소스)"
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="영상 제목 (content-file 미사용 시)"
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="영상 설명"
    )
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="공개 상태 (기본: private)"
    )
    parser.add_argument(
        "--thumbnail",
        type=str,
        default=None,
        help="썸네일 이미지 경로"
    )

    args = parser.parse_args()

    uploader = YouTubeUploader(args.channel)

    if args.content_file:
        result = uploader.upload_from_content_file(
            content_file=args.content_file,
            video_path=args.video,
            privacy_status=args.privacy,
            thumbnail_path=args.thumbnail
        )
    else:
        if not args.title:
            print("[ERROR] --content-file 또는 --title 중 하나는 필수입니다.", file=sys.stderr)
            sys.exit(1)
        result = uploader.upload_video(
            video_path=args.video,
            title=args.title,
            description=args.description,
            privacy_status=args.privacy,
            thumbnail_path=args.thumbnail
        )

    # GitHub Actions 출력 변수 설정
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"video_id={result.get('video_id', '')}\n")
            f.write(f"video_url={result.get('video_url', '')}\n")
            f.write(f"upload_status={result.get('status', 'unknown')}\n")

    print(f"\n결과: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
