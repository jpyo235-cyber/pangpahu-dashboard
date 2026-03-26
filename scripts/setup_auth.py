"""
setup_auth.py
=============
최초 YouTube OAuth2 인증을 수행하고 refresh_token을 발급받는 설정 스크립트.

이 스크립트는 로컬 환경에서 1회만 실행하면 됩니다.
발급받은 refresh_token을 GitHub Secrets에 저장하세요.

사용법:
    python setup_auth.py --client-secret ../config/client_secret.json --channel mydachshundtrio
"""

import json
import os
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]


def run_auth(client_secret_path: str, channel_label: str):
    """
    OAuth2 인증 플로우를 실행합니다.

    Args:
        client_secret_path: client_secret JSON 파일 경로
        channel_label: 채널 식별 라벨 (mydachshundtrio / drpangpsych)
    """
    if not os.path.exists(client_secret_path):
        print(f"[ERROR] 파일을 찾을 수 없습니다: {client_secret_path}")
        sys.exit(1)

    token_dir = Path(__file__).resolve().parent.parent / "config"
    token_dir.mkdir(parents=True, exist_ok=True)
    token_path = token_dir / f"token_{channel_label}.json"

    creds = None

    # 기존 토큰 확인
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds and creds.valid:
            print(f"[INFO] 기존 유효한 토큰이 있습니다: {token_path}")
            _print_token_info(creds, channel_label)
            return
        elif creds and creds.expired and creds.refresh_token:
            print("[INFO] 토큰 갱신 중...")
            creds.refresh(Request())
            _save_and_print(creds, token_path, channel_label)
            return

    # 새 인증 시작
    print(f"\n{'='*60}")
    print(f"YouTube OAuth2 인증 - {channel_label}")
    print(f"{'='*60}")
    print(f"\n[주의] 브라우저가 열리면 '{channel_label}' 채널의 Google 계정으로 로그인하세요.")
    print(f"[주의] 여러 채널이 있다면, 각 채널의 Google 계정으로 별도 인증해야 합니다.\n")

    input("준비되면 Enter를 누르세요...")

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

    _save_and_print(creds, token_path, channel_label)


def _save_and_print(creds, token_path, channel_label):
    """토큰을 저장하고 정보를 출력합니다."""
    # 토큰 파일 저장
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    print(f"\n[INFO] 토큰 파일 저장: {token_path}")

    _print_token_info(creds, channel_label)

    # 채널 정보 확인
    try:
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        if response.get("items"):
            ch = response["items"][0]["snippet"]
            print(f"\n[인증된 채널 정보]")
            print(f"  채널명: {ch['title']}")
            print(f"  설명: {ch.get('description', 'N/A')[:80]}")
    except Exception as e:
        print(f"[WARNING] 채널 정보 조회 실패: {e}")


def _print_token_info(creds, channel_label):
    """refresh_token 정보를 출력합니다."""
    env_name = f"YOUTUBE_REFRESH_TOKEN_{channel_label.upper()}"

    print(f"\n{'='*60}")
    print(f"[중요] GitHub Secrets에 아래 값을 저장하세요")
    print(f"{'='*60}")
    print(f"\n  Secret 이름: {env_name}")
    print(f"  Secret 값:")
    print(f"\n  {creds.refresh_token}")
    print(f"\n{'='*60}")
    print(f"\nGitHub 저장소 → Settings → Secrets and variables → Actions")
    print(f"→ New repository secret → 위 이름과 값을 입력")
    print(f"{'='*60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube OAuth2 초기 인증 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 닥스삼부자 채널 인증
  python setup_auth.py --client-secret ../config/client_secret.json --channel mydachshundtrio

  # DrPangPsych 채널 인증
  python setup_auth.py --client-secret ../config/client_secret.json --channel drpangpsych

[참고] 각 채널마다 해당 채널의 Google 계정으로 로그인해야 합니다.
        """
    )
    parser.add_argument(
        "--client-secret",
        type=str,
        required=True,
        help="client_secret JSON 파일 경로"
    )
    parser.add_argument(
        "--channel",
        type=str,
        required=True,
        choices=["mydachshundtrio", "drpangpsych"],
        help="인증할 채널 ID"
    )

    args = parser.parse_args()
    run_auth(args.client_secret, args.channel)


if __name__ == "__main__":
    main()
