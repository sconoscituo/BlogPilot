"""
분석 라우터
구글 서치 콘솔 및 애드센스 데이터를 조회하는 API 및 페이지 엔드포인트
"""
import logging

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.search_console import search_console_service
from app.services.adsense import adsense_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["분석"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """검색 성과 및 애드센스 대시보드 페이지"""
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "page": "analytics",
            "gemini_configured": settings.is_gemini_configured,
            "wordpress_configured": settings.is_wordpress_configured,
            "search_console_configured": bool(settings.GOOGLE_SEARCH_CONSOLE_CREDENTIALS),
            "adsense_configured": bool(settings.ADSENSE_ACCOUNT_ID),
            "unsplash_configured": bool(settings.UNSPLASH_ACCESS_KEY),
        },
    )


@router.get("/api/analytics/search-performance")
async def get_search_performance(
    start_date: str = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
    row_limit: int = Query(50, ge=1, le=200, description="반환할 키워드 수"),
):
    """
    구글 서치 콘솔 검색 성과 데이터 조회

    키워드별 클릭수, 노출수, CTR, 평균 순위를 반환합니다.
    API 자격증명이 없을 경우 데모 데이터를 반환합니다.
    """
    try:
        data = await search_console_service.get_search_performance(
            start_date=start_date,
            end_date=end_date,
            row_limit=row_limit,
        )
        return data
    except Exception as e:
        logger.error(f"검색 성과 조회 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"검색 성과 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}"},
        )


@router.get("/api/analytics/adsense-revenue")
async def get_adsense_revenue(
    start_date: str = Query(None, description="조회 시작일 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="조회 종료일 (YYYY-MM-DD)"),
):
    """
    애드센스 수익 데이터 조회

    일별/월별 수익, 페이지뷰, CPC, RPM을 반환합니다.
    API 자격증명이 없을 경우 데모 데이터를 반환합니다.
    """
    try:
        data = await adsense_service.get_revenue_data(
            start_date=start_date,
            end_date=end_date,
        )
        return data
    except Exception as e:
        logger.error(f"애드센스 수익 조회 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"수익 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}"},
        )
