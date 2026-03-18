"""
경쟁 분석 라우터
키워드 기반 경쟁 블로그 분석 API 및 페이지 엔드포인트
"""
import logging

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.competitor_analyzer import competitor_analyzer
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["경쟁 분석"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/competitors", response_class=HTMLResponse)
async def competitors_page(request: Request):
    """경쟁 분석 페이지"""
    return templates.TemplateResponse(
        "competitors.html",
        {
            "request": request,
            "page": "competitors",
            "gemini_configured": settings.is_gemini_configured,
            "wordpress_configured": settings.is_wordpress_configured,
        },
    )


@router.get("/api/competitors/analyze")
async def analyze_competitors(
    keyword: str = Query(..., description="분석할 키워드", min_length=1, max_length=100),
):
    """
    키워드 기반 경쟁 블로그 분석

    구글 상위 결과를 스크래핑하여 제목, 메타설명, 글 길이,
    H2 구조를 분석하고 더 나은 글 전략을 제안합니다.
    스크래핑 실패 시 데모 데이터를 반환합니다.
    """
    try:
        data = await competitor_analyzer.analyze_competitors(keyword)
        return data
    except Exception as e:
        logger.error(f"경쟁 분석 실패 (키워드: {keyword}): {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"경쟁 분석 중 오류가 발생했습니다: {str(e)}"},
        )
