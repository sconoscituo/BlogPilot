# BlogPilot - AI 블로그 자동화 플랫폼

## 필요한 API 키 및 환경변수

| 환경변수 | 설명 | 발급 URL |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini AI API 키 (콘텐츠 생성용) | https://aistudio.google.com/app/apikey |
| `APP_SECRET_KEY` | 앱 시크릿 키 (세션/보안용 임의 문자열) | - |
| `WORDPRESS_URL` | WordPress 사이트 URL (예: `https://myblog.com`) | - |
| `WORDPRESS_USERNAME` | WordPress 관리자 계정명 | - |
| `WORDPRESS_APP_PASSWORD` | WordPress 애플리케이션 비밀번호 | WordPress 관리자 → 사용자 → 애플리케이션 비밀번호 |
| `UNSPLASH_ACCESS_KEY` | Unsplash 이미지 API 키 | https://unsplash.com/developers |
| `NAVER_CLIENT_ID` | 네이버 API 클라이언트 ID (키워드 트렌드용) | https://developers.naver.com |
| `NAVER_CLIENT_SECRET` | 네이버 API 클라이언트 시크릿 | https://developers.naver.com |
| `GOOGLE_SEARCH_CONSOLE_CREDENTIALS` | 구글 서치 콘솔 OAuth 자격증명 JSON | https://console.cloud.google.com |
| `SEARCH_CONSOLE_SITE_URL` | 구글 서치 콘솔에 등록된 사이트 URL | - |
| `ADSENSE_ACCOUNT_ID` | 구글 애드센스 계정 ID | https://www.google.com/adsense |
| `DATABASE_URL` | 데이터베이스 연결 URL (기본: SQLite) | - |
| `SCHEDULER_TIMEZONE` | 스케줄러 타임존 (기본: `Asia/Seoul`) | - |

## GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|---|---|
| `GEMINI_API_KEY` | Gemini API 키 |
| `APP_SECRET_KEY` | 앱 시크릿 키 |
| `WORDPRESS_URL` | WordPress 사이트 URL |
| `WORDPRESS_USERNAME` | WordPress 계정명 |
| `WORDPRESS_APP_PASSWORD` | WordPress 앱 비밀번호 |
| `UNSPLASH_ACCESS_KEY` | Unsplash API 키 |
| `NAVER_CLIENT_ID` | 네이버 클라이언트 ID |
| `NAVER_CLIENT_SECRET` | 네이버 클라이언트 시크릿 |

## 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/sconoscituo/BlogPilot.git
cd BlogPilot

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 아래 항목 입력:
# GEMINI_API_KEY=your_gemini_api_key
# APP_SECRET_KEY=your_random_secret_key
# WORDPRESS_URL=https://your-blog.com
# WORDPRESS_USERNAME=admin
# WORDPRESS_APP_PASSWORD=xxxx xxxx xxxx xxxx

# 5. 서버 실행
uvicorn app.main:app --reload
```

서버 기동 후 http://localhost:8000 에서 웹 UI를, http://localhost:8000/docs 에서 API 문서를 확인할 수 있습니다.

## Docker로 실행

```bash
docker-compose up --build
```

## 주요 기능 사용법

### AI 콘텐츠 자동 생성
- Gemini AI가 키워드를 기반으로 SEO 최적화된 블로그 포스트를 자동 생성합니다.
- 기본 언어: 한국어 (`DEFAULT_LANGUAGE=ko`)
- 최대 토큰: 8,192 토큰

### WordPress 자동 발행
- 생성된 콘텐츠를 WordPress REST API를 통해 자동으로 발행합니다.
- WordPress 관리자 패널에서 **애플리케이션 비밀번호**를 먼저 생성해야 합니다.

### 이미지 자동 삽입
- Unsplash API를 통해 키워드에 맞는 이미지를 자동으로 가져와 포스트에 삽입합니다.
- `generated_images/` 디렉토리에 생성된 이미지가 저장됩니다.

### 네이버 키워드 트렌드 분석
- 네이버 DataLab API를 통해 키워드 검색 트렌드를 분석합니다.
- 최대 20개 키워드 동시 분석 가능

### 자동 스케줄링
- APScheduler를 사용해 지정된 시간에 자동으로 포스팅합니다.
- 타임존: `Asia/Seoul` (기본값)

## 프로젝트 구조

```
BlogPilot/
├── app/
│   ├── config.py               # 환경변수 설정
│   ├── database.py             # DB 연결 관리
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── content_templates/      # 콘텐츠 템플릿
│   ├── models/                 # SQLAlchemy 모델
│   ├── routers/                # API 라우터
│   ├── schemas/                # Pydantic 스키마
│   ├── services/               # 비즈니스 로직
│   ├── static/                 # 정적 파일 (CSS, JS)
│   └── templates/              # Jinja2 HTML 템플릿
├── generated_images/           # 생성된 이미지 저장소
├── tests/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
