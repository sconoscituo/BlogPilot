# BlogPilot

AI 블로그 자동화 + 애드센스 수익 도구. Gemini AI로 SEO 최적화 글을 자동 생성하고 WordPress에 포스팅하여 애드센스 수익을 창출합니다.

## 수익 구조

```
키워드 리서치 → Gemini AI 글 생성 → WordPress 자동 포스팅 → 구글 검색 노출 → 애드센스 광고 수익
```

- 키워드 볼륨이 높고 경쟁도가 낮은 롱테일 키워드 자동 탐색
- SEO 최적화 메타 태그, 제목, 소제목 자동 구성
- 스케줄러로 하루 N건 자동 발행 → 콘텐츠 누적 → 트래픽 증가

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 API | FastAPI (Python 3.12) |
| AI 콘텐츠 생성 | Google Gemini 1.5 Flash |
| 블로그 플랫폼 | WordPress (REST API v2) |
| 데이터베이스 | SQLite (aiosqlite) |
| 스케줄러 | APScheduler |
| 이미지 | Unsplash API |
| SEO 분석 | Google Search Console API |
| 컨테이너 | Docker |

## 프로젝트 구조

```
BlogPilot/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 환경변수 설정
│   ├── database.py          # SQLAlchemy 비동기 엔진
│   ├── models/              # ORM 모델
│   ├── routers/             # API 라우터
│   ├── services/            # 비즈니스 로직
│   │   ├── content_generator.py   # Gemini 글 생성
│   │   ├── wordpress_publisher.py # WordPress 포스팅
│   │   ├── keyword_researcher.py  # 키워드 리서치
│   │   └── scheduler.py           # 자동화 스케줄러
│   └── schemas/             # Pydantic 스키마
├── tests/
├── generated_images/        # 생성된 이미지 임시 저장
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 설치 및 실행

### 사전 요구사항

- Python 3.12+
- WordPress 사이트 (REST API 활성화 + 애플리케이션 비밀번호 발급)
- Google Gemini API Key

### 1. 저장소 클론

```bash
git clone https://github.com/sconoscituo/BlogPilot.git
cd BlogPilot
```

### 2. 가상환경 설정

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (.env)

```env
GEMINI_API_KEY=your_gemini_api_key_here

# WordPress 연동
WORDPRESS_URL=https://your-blog.com
WORDPRESS_USERNAME=your_wp_username
WORDPRESS_APP_PASSWORD=your_app_password_here

# 선택 사항
UNSPLASH_ACCESS_KEY=your_unsplash_key
GOOGLE_SEARCH_CONSOLE_CREDENTIALS=./gsc-credentials.json
SEARCH_CONSOLE_SITE_URL=https://your-blog.com
ADSENSE_ACCOUNT_ID=pub-xxxxxxxxxx
```

### 4. 서버 실행

```bash
uvicorn app.main:app --reload --port 8000
```

### Docker로 실행

```bash
docker compose up -d
```

## WordPress 연동 방법

### 1. WordPress REST API 활성화 확인

WordPress 기본 설치 시 REST API는 자동으로 활성화됩니다.
`https://your-blog.com/wp-json/wp/v2/posts` 접속 시 JSON 응답이 오면 정상입니다.

### 2. 애플리케이션 비밀번호 발급

1. WordPress 관리자 → 사용자 → 프로필
2. 하단 **애플리케이션 비밀번호** 섹션
3. 이름 입력 후 **새 애플리케이션 비밀번호 추가** 클릭
4. 생성된 비밀번호를 `.env`의 `WORDPRESS_APP_PASSWORD`에 입력

### 3. 연동 테스트

```bash
curl -X GET https://your-blog.com/wp-json/wp/v2/posts \
  -u "username:application_password"
```

## 자동화 스케줄

| 작업 | 주기 | 설명 |
|------|------|------|
| 키워드 리서치 | 매일 06:00 | 트렌딩 키워드 수집 |
| 콘텐츠 생성 | 매일 08:00 | Gemini로 글 작성 |
| WordPress 포스팅 | 매일 09:00 | 생성된 글 자동 발행 |
| SEO 리포트 | 매주 월요일 | Search Console 데이터 분석 |

스케줄 변경: `app/services/scheduler.py`에서 cron 표현식 수정

## API 엔드포인트

서버 실행 후 `http://localhost:8000/docs`에서 Swagger UI 확인

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스체크 |
| POST | `/api/v1/content/generate` | 글 즉시 생성 |
| POST | `/api/v1/content/publish` | WordPress 발행 |
| GET | `/api/v1/content/list` | 생성된 글 목록 |
| GET | `/api/v1/keywords/trending` | 트렌딩 키워드 조회 |
| GET | `/api/v1/seo/report` | SEO 리포트 |

## 환경 변수 목록

| 변수 | 필수 | 설명 |
|------|------|------|
| `GEMINI_API_KEY` | 필수 | Google AI Studio에서 발급 |
| `WORDPRESS_URL` | 필수 | WordPress 사이트 URL |
| `WORDPRESS_USERNAME` | 필수 | WordPress 관리자 계정 |
| `WORDPRESS_APP_PASSWORD` | 필수 | 애플리케이션 비밀번호 |
| `DATABASE_URL` | 선택 | DB URL (기본: SQLite) |
| `UNSPLASH_ACCESS_KEY` | 선택 | 글 대표 이미지 자동 삽입 |
| `GOOGLE_SEARCH_CONSOLE_CREDENTIALS` | 선택 | GSC 연동 JSON 경로 |
| `ADSENSE_ACCOUNT_ID` | 선택 | 애드센스 수익 추적 |

## 테스트

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## 라이선스

MIT
