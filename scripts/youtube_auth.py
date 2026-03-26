"""
youtube_auth.py
===============
YouTube Data API v3 OAuth2 인증 모듈.

두 가지 모드를 지원합니다:
1. 초기 인증 (로컬): 브라우저를 통한 최초 인증 및 refresh_token 발급
2. 헤드리스 인증 (CI/CD): refresh_token을 사용한 자동 토큰 갱신
"""

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube Data API v3 스코프
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def authenticate_local(client_secret_path: str, token_save_path: str = None) -> Credentials:
    """
    로컬 환경에서 브라우저 기반 OAuth2 인증을 수행합니다.
    최초 1회만 실행하면 되며, refresh_token을 발급받습니다.

    Args:
        client_secret_path: client_secret JSON 파일 경로
        token_save_path: 토큰 저장 경로 (기본: ./token.json)

    Returns:
        인증된 Credentials 객체
    """
    if token_save_path is None:
        token_save_path = str(Path(__file__).resolve().parent.parent / "config" / "token.json")

    creds = None

    # 기존 토큰 파일 확인
    if os.path.exists(token_save_path):
        creds = Credentials.from_authorized_user_file(token_save_path, SCOPES)

    # 토큰이 없거나 만료된 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] 토큰 갱신 중...")
            creds.refresh(Request())
        else:
            print("[INFO] 새로운 인증을 시작합니다. 브라우저가 열립니다...")
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path,
                SCOPES,
                redirect_uri="http://localhost"
            )
            creds = flow.run_local_server(
                port=8080,
                prompt="consent",
                access_type="offline"
            )

        # 토큰 저장
        Path(token_save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(token_save_path, "w") as f:
            f.write(creds.to_json())
        print(f"[INFO] 토큰 저장 완료: {token_save_path}")

        # refresh_token 출력 (GitHub Secrets에 저장용)
        if creds.refresh_token:
            print(f"\n{'='*60}")
            print(f"[중요] 아래 refresh_token을 GitHub Secrets에 저장하세요:")
            print(f"{'='*60}")
            print(f"{creds.refresh_token}")
            print(f"{'='*60}\n")

    return creds


def authenticate_headless(channel_id: str) -> Credentials:
    """
    CI/CD (GitHub Actions) 환경에서 refresh_token을 사용한 헤드리스 인증.
    환경 변수에서 클라이언트 설정과 refresh_token을 읽어옵니다.

    Args:
        channel_id: 채널 ID ('mydachshundtrio' 또는 'drpangpsych')

    Returns:
        인증된 Credentials 객체
    """
    # 환경 변수에서 클라이언트 설정 로드
    client_secret_json = os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
    if not client_secret_json:
        print("[ERROR] GOOGLE_CLIENT_SECRET_JSON 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    client_config = json.loads(client_secret_json)
    installed = client_config.get("installed", {})

    # 채널별 refresh_token 로드
    refresh_token_env = f"YOUTUBE_REFRESH_TOKEN_{channel_id.upper()}"
    refresh_token = os.environ.get(refresh_token_env)
    if not refresh_token:
        print(f"[ERROR] {refresh_token_env} 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    # Credentials 객체 생성
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=installed["token_uri"],
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
        scopes=SCOPES
    )

    # 토큰 갱신
    print("[INFO] 액세스 토큰 갱신 중...")
    creds.refresh(Request())
    print("[INFO] 토큰 갱신 완료")

    return creds


def get_youtube_service(creds: Credentials):
    """
    인증된 YouTube API 서비스 객체를 생성합니다.

    Args:
        creds: 인증된 Credentials 객체

    Returns:
        YouTube API 서비스 객체
    """
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def main():
    """로컬 인증 CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube OAuth2 인증 도구")
    parser.add_argument(
        "--client-secret",
        type=str,
        required=True,
        help="client_secret JSON 파일 경로"
    )
    parser.add_argument(
        "--token-path",
        type=str,
        default=None,
        help="토큰 저장 경로"
    )

    args = parser.parse_args()

    creds = authenticate_local(args.client_secret, args.token_path)

    # 인증 확인
    service = get_youtube_service(creds)
    response = service.channels().list(part="snippet", mine=True).execute()

    if response.get("items"):
        channel = response["items"][0]["snippet"]
        print(f"\n[SUCCESS] 인증 성공!")
        print(f"  채널명: {channel['title']}")
        print(f"  설명: {channel.get('description', 'N/A')[:50]}...")
    else:
        print("[WARNING] 인증은 성공했으나 채널 정보를 가져올 수 없습니다.")


if __name__ == "__main__":
    main()
