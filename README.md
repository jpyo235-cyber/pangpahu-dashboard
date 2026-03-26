# Pangpahu Dashboard - 유튜브 채널 자동화 시스템

이 프로젝트는 두 개의 유튜브 채널에 AI가 생성한 콘텐츠를 자동으로 업로드하는 GitHub Actions 기반 파이프라인입니다.

## 📺 지원 채널

1. **닥스삼부자 (@mydachshundtrio)**
   - **주제**: 닥스훈트 반려견 관련 국내 한글 콘텐츠
   - **업로드 스케줄**: 화, 목, 토 오전 9시 (KST)
2. **DrPangPsych (@drpangpsych)**
   - **주제**: 심리학, 정신건강 관련 글로벌 영어 콘텐츠
   - **업로드 스케줄**: 월, 수 오후 2시 (KST)

---

## 🛠 시스템 아키텍처

본 시스템은 다음 세 단계의 자동화 파이프라인으로 구성되어 있습니다:

1. **콘텐츠 생성 (`content_generator.py`)**
   - OpenAI GPT 모델을 활용하여 채널 성격에 맞는 영상 스크립트, 제목, 설명, 태그를 자동 생성합니다.
2. **영상 제작 (`video_creator.py`)**
   - OpenAI TTS(Text-to-Speech) API를 사용하여 자연스러운 내레이션 오디오를 생성합니다.
   - Python PIL 라이브러리로 제목 카드를 생성하고, `ffmpeg`를 이용해 오디오와 결합하여 MP4 영상을 만듭니다.
3. **유튜브 업로드 (`youtube_uploader.py`)**
   - YouTube Data API v3를 사용하여 완성된 영상과 썸네일을 지정된 채널에 자동 업로드합니다.

---

## 🚀 초기 설정 가이드

GitHub Actions에서 자동화가 동작하려면 초기 로컬 인증 및 시크릿 설정이 필요합니다.

### 1. 로컬 환경 구성

먼저 로컬 컴퓨터에 프로젝트를 클론하고 의존성을 설치합니다.

```bash
git clone https://github.com/your-username/pangpahu-dashboard.git
cd pangpahu-dashboard
pip install -r requirements.txt
```

### 2. Google API 클라이언트 시크릿 준비

1. 첨부된 `client_secret_*.json` 파일을 `config/client_secret.json` 이름으로 복사합니다. (이 파일은 `.gitignore`에 의해 커밋되지 않습니다.)

### 3. 채널별 최초 인증 (Refresh Token 발급)

각 채널에 영상을 업로드할 수 있는 권한(Refresh Token)을 얻어야 합니다. 터미널에서 다음 명령어를 실행하세요.

**닥스삼부자 채널 인증:**
```bash
python scripts/setup_auth.py --client-secret config/client_secret.json --channel mydachshundtrio
```
> 브라우저가 열리면 **반드시 닥스삼부자 채널이 연결된 구글 계정**으로 로그인하세요.

**DrPangPsych 채널 인증:**
```bash
python scripts/setup_auth.py --client-secret config/client_secret.json --channel drpangpsych
```
> 브라우저가 열리면 **반드시 DrPangPsych 채널이 연결된 구글 계정**으로 로그인하세요.

인증이 완료되면 터미널에 `1//0...` 형태의 **Refresh Token**이 출력됩니다. 이 값을 복사해둡니다.

### 4. GitHub Secrets 설정

GitHub 저장소의 **Settings > Secrets and variables > Actions** 메뉴로 이동하여 다음 4개의 Repository Secrets를 추가합니다.

| Secret 이름 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 (`sk-...`) |
| `GOOGLE_CLIENT_SECRET_JSON` | `client_secret.json` 파일의 **전체 텍스트 내용**을 그대로 복사하여 붙여넣기 |
| `YOUTUBE_REFRESH_TOKEN_MYDACHSHUNDTRIO` | 닥스삼부자 인증 시 발급받은 Refresh Token |
| `YOUTUBE_REFRESH_TOKEN_DRPANGPSYCH` | DrPangPsych 인증 시 발급받은 Refresh Token |

---

## 🔄 수동 실행 및 테스트

정해진 스케줄 외에도 GitHub Actions 탭에서 워크플로우를 수동으로 실행할 수 있습니다.

1. GitHub 저장소의 **Actions** 탭 클릭
2. 왼쪽 메뉴에서 실행할 채널 워크플로우 선택 (`닥스삼부자 - 콘텐츠 자동 업로드` 등)
3. **Run workflow** 버튼 클릭
   - `Content type`: 일반 영상(`script`) 또는 쇼츠(`shorts`) 선택
   - `Privacy status`: 업로드 시 공개 상태 (기본값 `private` 권장)
   - `Skip upload`: 체크 시 영상만 생성하고 업로드는 건너뜀 (테스트용)

---

## 📂 프로젝트 구조

```text
pangpahu-dashboard/
├── .github/
│   └── workflows/
│       ├── mydachshundtrio.yml  # 닥스삼부자 자동화 워크플로우
│       └── drpangpsych.yml      # DrPangPsych 자동화 워크플로우
├── config/
│   ├── channels.json            # 채널별 설정 (주제, 태그, 프롬프트 등)
│   └── (client_secret.json)     # (로컬 인증용 - 커밋 제외)
├── scripts/
│   ├── config_loader.py         # 설정 로드 유틸리티
│   ├── content_generator.py     # AI 콘텐츠(스크립트) 생성 모듈
│   ├── video_creator.py         # TTS 오디오 및 영상(MP4) 합성 모듈
│   ├── youtube_auth.py          # YouTube API 인증 모듈
│   ├── youtube_uploader.py      # YouTube 영상 업로드 모듈
│   ├── pipeline.py              # 전체 자동화 파이프라인 메인 스크립트
│   └── setup_auth.py            # 로컬 최초 인증 헬퍼 스크립트
├── requirements.txt             # 파이썬 의존성 패키지
└── README.md                    # 본 문서
```

## ⚠️ 주의사항

- **비용**: OpenAI API(GPT-4.1-mini, TTS) 사용에 따른 비용이 발생합니다.
- **할당량**: YouTube Data API v3는 일일 할당량(Quota) 제한이 있습니다. 영상 업로드는 1회당 약 1,600의 할당량을 소모하므로, 일일 무료 한도(10,000) 내에서 사용해야 합니다.
- 자동 업로드된 영상은 기본적으로 `private`(비공개) 상태로 업로드하도록 설정하여, 최종 검수 후 공개 전환하는 것을 권장합니다.
