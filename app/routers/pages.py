"""
HTML 페이지 라우터
Jinja2 템플릿을 사용하는 웹 UI 페이지 엔드포인트
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post, PostStatus
from app.models.keyword import Keyword
from app.models.schedule import Schedule
from app.models.template import Template
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["페이지"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """메인 대시보드 페이지"""
    from datetime import timedelta

    # 포스트 통계
    post_result = await db.execute(select(Post))
    all_posts = post_result.scalars().all()

    one_week_ago = datetime.utcnow() - timedelta(days=7)
    published = [p for p in all_posts if p.status == PostStatus.PUBLISHED]
    this_week = [p for p in published if p.published_at and p.published_at >= one_week_ago]
    pending = [p for p in all_posts if p.status in (PostStatus.GENERATED, PostStatus.SCHEDULED)]

    # 최근 발행 포스트 (최대 5개)
    recent_posts = sorted(
        [p for p in all_posts if p.status == PostStatus.PUBLISHED],
        key=lambda x: x.published_at or datetime.min,
        reverse=True,
    )[:5]

    # 키워드 통계
    kw_result = await db.execute(select(Keyword).where(Keyword.is_active == True))
    keywords = kw_result.scalars().all()
    unused_keywords = [k for k in keywords if not k.is_used]

    # 다가오는 스케줄 (최대 5개)
    sched_result = await db.execute(
        select(Schedule)
        .where(Schedule.status == "pending", Schedule.is_active == True)
        .order_by(Schedule.scheduled_time.asc())
        .limit(5)
    )
    upcoming_schedules = sched_result.scalars().all()

    # 주간 발행 차트 데이터 (최근 7일)
    weekly_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = sum(
            1 for p in published
            if p.published_at and day_start <= p.published_at <= day_end
        )
        weekly_data.append({"date": day.strftime("%m/%d"), "count": count})

    # 상태별 분포
    status_dist = {
        "발행됨": len(published),
        "대기중": len(pending),
        "초안": len([p for p in all_posts if p.status == PostStatus.DRAFT]),
        "실패": len([p for p in all_posts if p.status == PostStatus.FAILED]),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "page": "dashboard",
            "total_posts": len(all_posts),
            "published_count": len(published),
            "this_week_count": len(this_week),
            "pending_count": len(pending),
            "keyword_count": len(keywords),
            "unused_keyword_count": len(unused_keywords),
            "recent_posts": recent_posts,
            "upcoming_schedules": upcoming_schedules,
            "weekly_data": weekly_data,
            "status_dist": status_dist,
            "settings": settings,
        },
    )


@router.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request, db: AsyncSession = Depends(get_db)):
    """키워드 리서치 페이지"""
    result = await db.execute(
        select(Keyword).order_by(Keyword.priority.desc(), Keyword.created_at.desc()).limit(100)
    )
    keywords = result.scalars().all()

    return templates.TemplateResponse(
        "keywords.html",
        {
            "request": request,
            "page": "keywords",
            "keywords": keywords,
            "total": len(keywords),
        },
    )


@router.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request, db: AsyncSession = Depends(get_db)):
    """AI 글 생성 페이지"""
    # 활성 템플릿 목록
    tmpl_result = await db.execute(
        select(Template).where(Template.is_active == True).order_by(Template.is_default.desc())
    )
    templates_list = tmpl_result.scalars().all()

    # 미사용 키워드 목록
    kw_result = await db.execute(
        select(Keyword)
        .where(Keyword.is_active == True, Keyword.is_used == False)
        .order_by(Keyword.priority.desc(), Keyword.difficulty_score.asc())
        .limit(50)
    )
    keywords = kw_result.scalars().all()

    return templates.TemplateResponse(
        "generate.html",
        {
            "request": request,
            "page": "generate",
            "templates_list": templates_list,
            "keywords": keywords,
            "post_types": [
                {"value": "informational", "label": "정보성 글"},
                {"value": "review", "label": "리뷰 글"},
                {"value": "comparison", "label": "비교 글"},
                {"value": "listicle", "label": "리스트형 글"},
            ],
        },
    )


@router.get("/posts", response_class=HTMLResponse)
async def posts_page(request: Request, db: AsyncSession = Depends(get_db)):
    """포스트 관리 페이지"""
    result = await db.execute(
        select(Post).order_by(Post.created_at.desc()).limit(100)
    )
    posts = result.scalars().all()

    # 상태별 개수
    status_counts = {}
    for post in posts:
        status_counts[post.status] = status_counts.get(post.status, 0) + 1

    return templates.TemplateResponse(
        "posts.html",
        {
            "request": request,
            "page": "posts",
            "posts": posts,
            "total": len(posts),
            "status_counts": status_counts,
            "is_wordpress_configured": settings.is_wordpress_configured,
        },
    )


@router.get("/schedules", response_class=HTMLResponse)
async def schedules_page(request: Request, db: AsyncSession = Depends(get_db)):
    """스케줄 관리 페이지"""
    now = datetime.utcnow()

    # 발행 가능한 포스트 (GENERATED 상태)
    post_result = await db.execute(
        select(Post)
        .where(Post.status == PostStatus.GENERATED)
        .order_by(Post.created_at.desc())
        .limit(50)
    )
    publishable_posts = post_result.scalars().all()

    # 스케줄 목록
    sched_result = await db.execute(
        select(Schedule).order_by(Schedule.scheduled_time.asc()).limit(50)
    )
    schedules = sched_result.scalars().all()

    return templates.TemplateResponse(
        "schedules.html",
        {
            "request": request,
            "page": "schedules",
            "schedules": schedules,
            "publishable_posts": publishable_posts,
            "now": now,
            "current_year": now.year,
            "current_month": now.month,
        },
    )


@router.get("/templates-page", response_class=HTMLResponse)
async def templates_page(request: Request, db: AsyncSession = Depends(get_db)):
    """템플릿 관리 페이지"""
    result = await db.execute(
        select(Template).order_by(Template.is_default.desc(), Template.usage_count.desc())
    )
    tmpl_list = result.scalars().all()

    return templates.TemplateResponse(
        "templates_page.html",
        {
            "request": request,
            "page": "templates",
            "templates": tmpl_list,
            "total": len(tmpl_list),
            "template_types": [
                {"value": "informational", "label": "정보성", "icon": "📝"},
                {"value": "review", "label": "리뷰", "icon": "⭐"},
                {"value": "comparison", "label": "비교", "icon": "🔍"},
                {"value": "listicle", "label": "리스트형", "icon": "📋"},
            ],
        },
    )
