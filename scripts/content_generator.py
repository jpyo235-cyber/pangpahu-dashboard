"""
content_generator.py
====================
OpenAI API를 활용하여 각 채널에 맞는 유튜브 콘텐츠를 자동 생성하는 모듈.
- 닥스삼부자: 닥스훈트/반려견 관련 한국어 콘텐츠
- DrPangPsych: 심리학/정신건강 관련 영어 콘텐츠
"""

import json
import random
import sys
from datetime import datetime
from openai import OpenAI

from config_loader import get_openai_api_key, load_channel_config


# ──────────────────────────────────────────────
# 프롬프트 템플릿
# ──────────────────────────────────────────────

PROMPT_TEMPLATES = {
    "ko": {
        "script": """당신은 유튜브 채널 '닥스삼부자'의 전문 콘텐츠 크리에이터입니다.
닥스훈트 세 마리와 함께하는 반려견 채널로, 따뜻하고 친근한 톤으로 콘텐츠를 만듭니다.

오늘의 주제: {topic}

다음 형식으로 유튜브 영상 스크립트를 작성해주세요:

1. **제목**: 클릭을 유도하는 매력적인 유튜브 제목 (50자 이내)
2. **설명**: 영상 설명란에 들어갈 텍스트 (200자 내외)
3. **태그**: 관련 태그 10개 (쉼표로 구분)
4. **스크립트**: 3-5분 분량의 내레이션 스크립트
   - 인트로 (시청자 인사 및 주제 소개)
   - 본문 (핵심 내용 3-4개 포인트)
   - 아웃트로 (구독/좋아요 유도 및 마무리)

반드시 JSON 형식으로 응답해주세요:
{{
    "title": "영상 제목",
    "description": "영상 설명",
    "tags": ["태그1", "태그2", ...],
    "script": "전체 스크립트 텍스트",
    "thumbnail_prompt": "썸네일 이미지 생성을 위한 영어 프롬프트"
}}""",
        "shorts": """당신은 유튜브 채널 '닥스삼부자'의 Shorts 콘텐츠 크리에이터입니다.

주제: {topic}

60초 이내의 유튜브 Shorts 스크립트를 작성해주세요.
짧고 임팩트 있게, 핵심만 전달하세요.

JSON 형식으로 응답:
{{
    "title": "Shorts 제목 (30자 이내)",
    "description": "짧은 설명",
    "tags": ["태그1", "태그2", ...],
    "script": "60초 분량 스크립트",
    "thumbnail_prompt": "썸네일 이미지 생성을 위한 영어 프롬프트"
}}"""
    },
    "en": {
        "script": """You are a professional content creator for the YouTube channel 'DrPangPsych'.
This channel provides psychology insights, mental health tips, and self-improvement advice
in a warm, professional, and accessible tone.

Today's topic: {topic}

Please create a YouTube video script in the following format:

1. **Title**: An engaging, clickable YouTube title (under 60 characters)
2. **Description**: Video description text (around 150-200 words)
3. **Tags**: 10 relevant tags (comma-separated)
4. **Script**: A 3-5 minute narration script
   - Intro (greeting and topic introduction)
   - Body (3-4 key points with examples)
   - Outro (call to action for subscribe/like and closing)

Respond strictly in JSON format:
{{
    "title": "Video title",
    "description": "Video description",
    "tags": ["tag1", "tag2", ...],
    "script": "Full script text",
    "thumbnail_prompt": "English prompt for thumbnail image generation"
}}""",
        "shorts": """You are a YouTube Shorts content creator for 'DrPangPsych'.

Topic: {topic}

Create a YouTube Shorts script (under 60 seconds).
Keep it punchy, insightful, and memorable.

Respond in JSON format:
{{
    "title": "Shorts title (under 40 chars)",
    "description": "Brief description",
    "tags": ["tag1", "tag2", ...],
    "script": "60-second script",
    "thumbnail_prompt": "English prompt for thumbnail image generation"
}}"""
    }
}


class ContentGenerator:
    """AI 기반 유튜브 콘텐츠 생성기."""

    def __init__(self, channel_id: str):
        """
        Args:
            channel_id: 'mydachshundtrio' 또는 'drpangpsych'
        """
        self.channel_id = channel_id
        self.config = load_channel_config(channel_id)
        self.language = self.config["language"]
        self.client = OpenAI(api_key=get_openai_api_key())
        self.model = "gpt-4.1-mini"

    def _select_topic(self) -> str:
        """
        채널 테마 목록에서 오늘의 주제를 선택합니다.
        날짜 기반 시드를 사용하여 동일 날짜에는 같은 주제가 선택됩니다.
        """
        themes = self.config["content_themes"]
        today = datetime.utcnow().strftime("%Y-%m-%d")
        seed = hash(f"{self.channel_id}-{today}")
        random.seed(seed)
        return random.choice(themes)

    def _call_openai(self, prompt: str) -> dict:
        """
        OpenAI API를 호출하여 JSON 응답을 파싱합니다.

        Args:
            prompt: 완성된 프롬프트 문자열

        Returns:
            파싱된 JSON 딕셔너리
        """
        print(f"[INFO] OpenAI API 호출 중 (모델: {self.model})...")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional YouTube content creator. "
                               "Always respond with valid JSON only, no markdown formatting."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content.strip()

        # JSON 파싱
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # 마크다운 코드 블록 제거 후 재시도
            cleaned = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)

        return result

    def generate_video_content(self, content_type: str = "script", custom_topic: str = None) -> dict:
        """
        유튜브 영상 콘텐츠를 생성합니다.

        Args:
            content_type: 'script' (일반 영상) 또는 'shorts'
            custom_topic: 사용자 지정 주제 (None이면 자동 선택)

        Returns:
            생성된 콘텐츠 딕셔너리:
            {
                "title": str,
                "description": str,
                "tags": list[str],
                "script": str,
                "thumbnail_prompt": str,
                "metadata": {
                    "channel_id": str,
                    "content_type": str,
                    "topic": str,
                    "generated_at": str,
                    "language": str
                }
            }
        """
        topic = custom_topic or self._select_topic()
        print(f"[INFO] 콘텐츠 생성 시작 - 채널: {self.config['channel_name']}, 주제: {topic}")

        # 프롬프트 구성
        template = PROMPT_TEMPLATES[self.language][content_type]
        prompt = template.format(topic=topic)

        # AI 생성
        result = self._call_openai(prompt)

        # 기본 태그 병합
        default_tags = self.config.get("default_tags", [])
        ai_tags = result.get("tags", [])
        merged_tags = list(dict.fromkeys(ai_tags + default_tags))  # 중복 제거, 순서 유지

        # 설명 템플릿 적용
        desc_template = self.config.get("description_template", "{description}")
        full_description = desc_template.format(description=result.get("description", ""))

        # 최종 결과 구성
        content = {
            "title": result.get("title", "Untitled"),
            "description": full_description,
            "tags": merged_tags[:15],  # YouTube 태그 제한 고려
            "script": result.get("script", ""),
            "thumbnail_prompt": result.get("thumbnail_prompt", ""),
            "metadata": {
                "channel_id": self.channel_id,
                "channel_name": self.config["channel_name"],
                "content_type": content_type,
                "topic": topic,
                "generated_at": datetime.utcnow().isoformat(),
                "language": self.language,
                "category_id": self.config["category_id"]
            }
        }

        print(f"[INFO] 콘텐츠 생성 완료 - 제목: {content['title']}")
        return content

    def save_content(self, content: dict, output_dir: str = None) -> str:
        """
        생성된 콘텐츠를 JSON 파일로 저장합니다.

        Args:
            content: 생성된 콘텐츠 딕셔너리
            output_dir: 저장 디렉토리 (기본: assets/)

        Returns:
            저장된 파일 경로
        """
        from pathlib import Path

        if output_dir is None:
            output_dir = str(Path(__file__).resolve().parent.parent / "assets")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.channel_id}_{timestamp}.json"
        filepath = Path(output_dir) / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

        print(f"[INFO] 콘텐츠 저장 완료: {filepath}")
        return str(filepath)


def main():
    """CLI 진입점."""
    import argparse

    parser = argparse.ArgumentParser(description="AI 유튜브 콘텐츠 생성기")
    parser.add_argument(
        "channel",
        choices=["mydachshundtrio", "drpangpsych"],
        help="대상 채널 ID"
    )
    parser.add_argument(
        "--type",
        choices=["script", "shorts"],
        default="script",
        help="콘텐츠 유형 (기본: script)"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="사용자 지정 주제 (미지정 시 자동 선택)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="출력 디렉토리"
    )

    args = parser.parse_args()

    generator = ContentGenerator(args.channel)
    content = generator.generate_video_content(
        content_type=args.type,
        custom_topic=args.topic
    )
    filepath = generator.save_content(content, output_dir=args.output_dir)

    # GitHub Actions 출력 변수 설정
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"content_file={filepath}\n")
            f.write(f"video_title={content['title']}\n")

    print(f"\n{'='*60}")
    print(f"생성 완료!")
    print(f"  채널: {content['metadata']['channel_name']}")
    print(f"  제목: {content['title']}")
    print(f"  파일: {filepath}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
