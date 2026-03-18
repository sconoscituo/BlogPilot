"""
BlogPilot - AI 블로그 자동화 + AdSense 수익화 시스템
FastAPI 메인 애플리케이션 진입점
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import keywords, posts, publish, schedules, templates, pages, analytics, competitors
from app.services.scheduler import publish_scheduler

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 수명 주기 관리
    시작 시: DB 초기화, 기본 데이터 삽입, 스케줄러 시작
    종료 시: 스케줄러 종료
    """
    # --- 시작 ---
    logger.info("BlogPilot 시작 중...")

    # 데이터베이스 테이블 초기화
    await init_db()
    logger.info("데이터베이스 초기화 완료")

    # 기본 템플릿 데이터 삽입
    await _seed_default_templates()

    # 이미지 저장 디렉토리 생성
    os.makedirs(settings.GENERATED_IMAGES_DIR, exist_ok=True)

    # 발행 스케줄러 시작
    publish_scheduler.start()
    logger.info("발행 스케줄러 시작 완료")

    # 설정 상태 로그
    logger.info(f"Gemini API: {'설정됨' if settings.is_gemini_configured else '미설정'}")
    logger.info(f"WordPress: {'설정됨' if settings.is_wordpress_configured else '미설정'}")
    logger.info(f"서버 주소: http://0.0.0.0:8000")

    yield

    # --- 종료 ---
    logger.info("BlogPilot 종료 중...")
    publish_scheduler.shutdown()
    logger.info("스케줄러 종료 완료")


async def _seed_default_templates():
    """앱 시작 시 기본 템플릿 데이터 삽입"""
    try:
        from app.database import AsyncSessionLocal
        from app.models.template import Template
        from app.content_templates_data import DEFAULT_TEMPLATES
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Template).limit(1))
            if result.scalar_one_or_none() is None:
                # 템플릿이 없으면 기본 템플릿 삽입
                for tmpl_data in DEFAULT_TEMPLATES:
                    template = Template(**tmpl_data)
                    db.add(template)
                await db.commit()
                logger.info(f"{len(DEFAULT_TEMPLATES)}개 기본 템플릿 삽입 완료")
    except Exception as e:
        logger.error(f"기본 템플릿 삽입 실패: {e}")


# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="BlogPilot",
    description="AI 블로그 자동화 + AdSense 수익화 시스템",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount(
    "/generated_images",
    StaticFiles(directory=settings.GENERATED_IMAGES_DIR),
    name="generated_images",
)

# 라우터 등록
app.include_router(pages.router)           # HTML 페이지 (GET /)
app.include_router(keywords.router)        # /api/keywords
app.include_router(posts.router)           # /api/posts
app.include_router(publish.router)         # /api/publish
app.include_router(schedules.router)       # /api/schedules
app.include_router(templates.router)       # /api/templates
app.include_router(analytics.router)       # /analytics, /api/analytics
app.include_router(competitors.router)     # /competitors, /api/competitors


@app.get("/health")
async def health_check():
    """서버 상태 확인 엔드포인트"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_configured": settings.is_gemini_configured,
        "wordpress_configured": settings.is_wordpress_configured,
    }
