"""
config_loader.py
================
채널 설정 및 환경 변수를 로드하는 유틸리티 모듈.
"""

import json
import os
import sys
from pathlib import Path


# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_DIR = PROJECT_ROOT / "assets"


def load_channel_config(channel_id: str) -> dict:
    """
    채널 ID에 해당하는 설정을 로드합니다.

    Args:
        channel_id: 'mydachshundtrio' 또는 'drpangpsych'

    Returns:
        채널 설정 딕셔너리
    """
    config_path = CONFIG_DIR / "channels.json"
    if not config_path.exists():
        raise FileNotFoundError(f"채널 설정 파일을 찾을 수 없습니다: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    channels = config.get("channels", {})
    if channel_id not in channels:
        raise ValueError(
            f"알 수 없는 채널 ID: {channel_id}. "
            f"사용 가능: {list(channels.keys())}"
        )

    return channels[channel_id]


def get_env_var(name: str, required: bool = True, default: str = None) -> str:
    """
    환경 변수를 가져옵니다.

    Args:
        name: 환경 변수 이름
        required: 필수 여부
        default: 기본값

    Returns:
        환경 변수 값
    """
    value = os.environ.get(name, default)
    if required and not value:
        print(f"[ERROR] 필수 환경 변수가 설정되지 않았습니다: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def get_google_client_config() -> dict:
    """
    Google OAuth2 클라이언트 설정을 환경 변수에서 로드합니다.

    Returns:
        클라이언트 설정 딕셔너리
    """
    client_secret_json = get_env_var("GOOGLE_CLIENT_SECRET_JSON")
    try:
        return json.loads(client_secret_json)
    except json.JSONDecodeError as e:
        print(f"[ERROR] GOOGLE_CLIENT_SECRET_JSON 파싱 실패: {e}", file=sys.stderr)
        sys.exit(1)


def get_refresh_token(channel_id: str) -> str:
    """
    채널별 YouTube OAuth2 리프레시 토큰을 가져옵니다.

    Args:
        channel_id: 채널 ID

    Returns:
        리프레시 토큰 문자열
    """
    env_name = f"YOUTUBE_REFRESH_TOKEN_{channel_id.upper()}"
    return get_env_var(env_name)


def get_openai_api_key() -> str:
    """OpenAI API 키를 가져옵니다."""
    return get_env_var("OPENAI_API_KEY")


if __name__ == "__main__":
    # 테스트용
    print("=== 채널 설정 로드 테스트 ===")
    for cid in ["mydachshundtrio", "drpangpsych"]:
        cfg = load_channel_config(cid)
        print(f"\n[{cid}]")
        print(f"  채널명: {cfg['channel_name']}")
        print(f"  언어: {cfg['language']}")
        print(f"  스케줄: {cfg['schedule']['days']}")
        print(f"  테마 수: {len(cfg['content_themes'])}")
