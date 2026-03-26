# Pangpahu Dashboard - 상세 설정 가이드

이 문서는 유튜브 채널 자동화 시스템의 전체 설정 과정을 단계별로 안내합니다.

---

## 목차

1. [사전 준비물](#1-사전-준비물)
2. [Google Cloud Console 설정](#2-google-cloud-console-설정)
3. [로컬 환경 구성](#3-로컬-환경-구성)
4. [채널별 OAuth2 인증](#4-채널별-oauth2-인증)
5. [GitHub 저장소 설정](#5-github-저장소-설정)
6. [GitHub Secrets 등록](#6-github-secrets-등록)
7. [워크플로우 테스트](#7-워크플로우-테스트)
8. [운영 및 모니터링](#8-운영-및-모니터링)
9. [문제 해결](#9-문제-해결)

---

## 1. 사전 준비물

시스템을 구동하기 위해 다음이 필요합니다.

| 항목 | 설명 | 비고 |
|---|---|---|
| GitHub 계정 | 저장소 및 Actions 실행 | 무료 플랜 사용 가능 |
| OpenAI API 키 | GPT-4.1-mini 및 TTS API 호출 | `sk-...` 형태 |
| Google Cloud 프로젝트 | YouTube Data API v3 활성화 | 이미 생성됨 (sage-philosophy-447416-b9) |
| Google OAuth2 클라이언트 시크릿 | API 인증용 JSON 파일 | 첨부 파일 제공됨 |
| Python 3.11 이상 | 로컬 초기 인증 시 필요 | 이후에는 GitHub Actions에서 실행 |

---

## 2. Google Cloud Console 설정

첨부된 `client_secret` 파일이 이미 프로젝트 `sage-philosophy-447416-b9`에 연결되어 있습니다. 다만, YouTube Data API v3가 활성화되어 있는지 확인해야 합니다.

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속합니다.
2. 프로젝트 `sage-philosophy-447416-b9`를 선택합니다.
3. 왼쪽 메뉴에서 **API 및 서비스 > 라이브러리**로 이동합니다.
4. "YouTube Data API v3"를 검색하여 **사용 설정**이 되어 있는지 확인합니다.
5. **OAuth 동의 화면**에서 테스트 사용자로 두 채널의 구글 계정 이메일을 추가합니다. (앱이 "테스트" 상태인 경우 필수)

---

## 3. 로컬 환경 구성

```bash
# 저장소 클론
git clone https://github.com/your-username/pangpahu-dashboard.git
cd pangpahu-dashboard

# Python 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 클라이언트 시크릿 파일 배치
cp /path/to/client_secret_516789022827_*.json config/client_secret.json
```

---

## 4. 채널별 OAuth2 인증

이 단계는 각 채널마다 **1회만** 수행하면 됩니다. Refresh Token은 만료되지 않는 한 계속 사용할 수 있습니다.

### 4-1. 닥스삼부자 채널 인증

```bash
cd pangpahu-dashboard
python scripts/setup_auth.py \
  --client-secret config/client_secret.json \
  --channel mydachshundtrio
```

실행하면 다음과 같은 과정이 진행됩니다.

1. 터미널에 안내 메시지가 표시되고, Enter를 누르면 브라우저가 열립니다.
2. **닥스삼부자 채널이 연결된 구글 계정**으로 로그인합니다.
3. "이 앱은 Google에서 확인하지 않았습니다" 경고가 나타나면 **고급 > (앱 이름)(으)로 이동**을 클릭합니다.
4. 요청된 권한(YouTube 관리)을 **허용**합니다.
5. 터미널에 Refresh Token이 출력됩니다. 이 값을 복사합니다.

```
============================================================
[중요] GitHub Secrets에 아래 값을 저장하세요
============================================================

  Secret 이름: YOUTUBE_REFRESH_TOKEN_MYDACHSHUNDTRIO
  Secret 값:

  1//0abc...xyz

============================================================
```

### 4-2. DrPangPsych 채널 인증

```bash
python scripts/setup_auth.py \
  --client-secret config/client_secret.json \
  --channel drpangpsych
```

동일한 과정을 **DrPangPsych 채널의 구글 계정**으로 진행합니다.

> **중요**: 두 채널이 서로 다른 구글 계정에 연결되어 있다면, 각각의 계정으로 별도 인증해야 합니다. 같은 계정이라면 동일한 Refresh Token을 두 시크릿에 모두 사용할 수 있습니다.

---

## 5. GitHub 저장소 설정

### 5-1. 저장소 생성 및 코드 푸시

```bash
cd pangpahu-dashboard
git init
git add .
git commit -m "Initial commit: YouTube automation pipeline"
git branch -M main
git remote add origin https://github.com/your-username/pangpahu-dashboard.git
git push -u origin main
```

### 5-2. GitHub Actions 활성화 확인

저장소의 **Actions** 탭에서 워크플로우가 표시되는지 확인합니다. `.github/workflows/` 디렉토리에 두 개의 YAML 파일이 있으므로 자동으로 인식됩니다.

---

## 6. GitHub Secrets 등록

GitHub 저장소 페이지에서 **Settings > Secrets and variables > Actions > New repository secret**으로 이동하여 다음 4개의 시크릿을 등록합니다.

| Secret 이름 | 값 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 (예: `sk-proj-abc123...`) |
| `GOOGLE_CLIENT_SECRET_JSON` | `client_secret.json` 파일의 전체 내용을 그대로 붙여넣기 |
| `YOUTUBE_REFRESH_TOKEN_MYDACHSHUNDTRIO` | 4-1 단계에서 발급받은 Refresh Token |
| `YOUTUBE_REFRESH_TOKEN_DRPANGPSYCH` | 4-2 단계에서 발급받은 Refresh Token |

`GOOGLE_CLIENT_SECRET_JSON`에는 JSON 파일의 전체 텍스트를 그대로 복사하여 붙여넣습니다.

```json
{"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","project_id":"YOUR_PROJECT_ID","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"YOUR_CLIENT_SECRET","redirect_uris":["http://localhost"]}}
```

---

## 7. 워크플로우 테스트

시크릿 등록이 완료되면 수동 실행으로 테스트합니다.

1. GitHub 저장소의 **Actions** 탭으로 이동합니다.
2. 왼쪽에서 테스트할 워크플로우를 선택합니다.
3. **Run workflow** 버튼을 클릭합니다.
4. 옵션을 설정합니다.
   - `Privacy status`를 **private**으로 설정하여 비공개 업로드합니다.
   - `Skip upload`를 체크하면 콘텐츠 생성만 테스트할 수 있습니다.
5. 실행 결과를 확인합니다. 성공 시 Artifacts에서 생성된 파일을 다운로드할 수 있습니다.

---

## 8. 운영 및 모니터링

### 자동 실행 스케줄

정상적으로 설정되면 다음 스케줄에 따라 자동 실행됩니다.

| 채널 | 요일 | 시간 (KST) | cron (UTC) |
|---|---|---|---|
| 닥스삼부자 | 화, 목, 토 | 오전 9:00 | `0 0 * * 2,4,6` |
| DrPangPsych | 월, 수 | 오후 2:00 | `0 5 * * 1,3` |

### 비용 관리

| 서비스 | 예상 비용 (1회 실행 기준) | 비고 |
|---|---|---|
| OpenAI GPT-4.1-mini | 약 $0.01~0.03 | 스크립트 생성 |
| OpenAI TTS | 약 $0.02~0.05 | 3~5분 분량 오디오 |
| YouTube Data API | 무료 (할당량 내) | 일일 10,000 단위 |
| GitHub Actions | 무료 (2,000분/월) | Public 저장소는 무제한 |

### 모니터링 방법

- **GitHub Actions 탭**: 각 실행의 성공/실패 상태와 로그를 확인할 수 있습니다.
- **Artifacts**: 각 실행에서 생성된 콘텐츠 JSON, 오디오, 영상 파일을 다운로드할 수 있습니다 (30일 보관).
- **Step Summary**: 각 실행 결과의 요약(제목, Video ID, URL)이 자동으로 표시됩니다.

---

## 9. 문제 해결

### Refresh Token이 만료된 경우

Google OAuth2 Refresh Token은 일반적으로 만료되지 않지만, 다음 상황에서 무효화될 수 있습니다.

- 사용자가 Google 계정 설정에서 앱 액세스를 취소한 경우
- 6개월 이상 사용하지 않은 경우
- Google Cloud 프로젝트가 "테스트" 상태이고 7일이 경과한 경우

이 경우 4단계의 인증 과정을 다시 수행하고, 새 Refresh Token으로 GitHub Secret을 업데이트하면 됩니다.

> **팁**: Google Cloud Console에서 OAuth 동의 화면의 게시 상태를 "프로덕션"으로 변경하면 토큰 만료 문제를 방지할 수 있습니다. 단, Google의 검토가 필요할 수 있습니다.

### YouTube API 할당량 초과

YouTube Data API v3의 일일 할당량(기본 10,000 단위)을 초과하면 업로드가 실패합니다. 영상 업로드 1회에 약 1,600 단위가 소모되므로, 하루 최대 6회 정도 업로드가 가능합니다. 현재 스케줄(하루 최대 1회)에서는 문제가 되지 않습니다.

### OpenAI API 오류

API 키가 유효하지 않거나 잔액이 부족한 경우 콘텐츠 생성 단계에서 실패합니다. OpenAI 대시보드에서 API 키 상태와 사용량을 확인하세요.

---

*이 문서는 Pangpahu Dashboard 프로젝트의 설정 가이드입니다. 문의 사항이 있으면 GitHub Issues를 활용해주세요.*
