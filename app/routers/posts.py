"""
포스트 관리 API 라우터
블로그 포스트 생성, 조회, 수정, 삭제 및 AI 생성 엔드포인트
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post, PostStatus, PostType
from app.models.template import Template
from app.models.keyword import Keyword
from app.schemas.post import PostCreate, PostUpdate, PostResponse, PostGenerateRequest
from app.services.content_generator import content_generator
from app.services.image_generator import image_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/posts", tags=["포스트"])


@router.get("/", response_model=list[PostResponse])
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    post_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """포스트 목록 조회"""
    query = select(Post).order_by(Post.created_at.desc())

    if status:
        query = query.where(Post.status == status)
    if post_type:
        query = query.where(Post.post_type == post_type)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/generate", response_model=PostResponse, status_code=201)
async def generate_post(
    request: PostGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    AI로 블로그 포스트 자동 생성
    Gemini API를 사용하여 SEO 최적화 콘텐츠 생성
    """
    # 템플릿 조회 (있는 경우)
    custom_system_prompt = None
    custom_user_prompt = None

    if request.template_id:
        tmpl_result = await db.execute(
            select(Template).where(Template.id == request.template_id)
        )
        template = tmpl_result.scalar_one_or_none()
        if template:
            custom_system_prompt = template.system_prompt
            custom_user_prompt = template.user_prompt_template

    try:
        # AI 콘텐츠 생성
        generated = await content_generator.generate_post(
            primary_keyword=request.primary_keyword,
            secondary_keywords=request.secondary_keywords or "",
            post_type=request.post_type,
            target_word_count=request.target_word_count,
            custom_system_prompt=custom_system_prompt,
            custom_user_prompt=custom_user_prompt,
        )

        # 썸네일 이미지 생성
        image_path = None
        try:
            image_path = image_generator.generate_thumbnail(
                title=generated["title"],
                keyword=request.primary_keyword,
                post_type=request.post_type,
            )
        except Exception as img_err:
            logger.warning(f"썸네일 생성 실패 (계속 진행): {img_err}")

        # DB 저장
        post = Post(
            title=generated["title"],
            slug=generated["slug"],
            content=generated["content"],
            meta_description=generated.get("meta_description"),
            primary_keyword=request.primary_keyword,
            secondary_keywords=request.secondary_keywords,
            post_type=request.post_type,
            status=PostStatus.GENERATED,
            seo_score=generated.get("seo_score"),
            word_count=generated.get("word_count"),
            keyword_density=generated.get("keyword_density"),
            readability_score=generated.get("readability_score"),
            featured_image_path=image_path,
            template_id=request.template_id,
        )
        db.add(post)
        await db.flush()
        await db.refresh(post)

        # 키워드 사용 표시
        kw_result = await db.execute(
            select(Keyword).where(Keyword.keyword == request.primary_keyword)
        )
        keyword_obj = kw_result.scalar_one_or_none()
        if keyword_obj:
            keyword_obj.is_used = True

        # 템플릿 사용 횟수 증가
        if request.template_id:
            tmpl_result2 = await db.execute(
                select(Template).where(Template.id == request.template_id)
            )
            tmpl = tmpl_result2.scalar_one_or_none()
            if tmpl:
                tmpl.usage_count += 1

        return post

    except Exception as e:
        logger.error(f"포스트 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"포스트 생성 실패: {str(e)}")


@router.post("/", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    db: AsyncSession = Depends(get_db),
):
    """포스트 수동 생성 (빈 초안)"""
    post = Post(
        title=f"{post_data.primary_keyword} - 초안",
        primary_keyword=post_data.primary_keyword,
        secondary_keywords=post_data.secondary_keywords,
        post_type=post_data.post_type,
        status=PostStatus.DRAFT,
        template_id=post_data.template_id,
        scheduled_at=post_data.scheduled_at,
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)
    return post


@router.get("/stats/summary")
async def get_post_stats(db: AsyncSession = Depends(get_db)):
    """포스트 통계 요약 (대시보드용)"""
    result = await db.execute(select(Post))
    all_posts = result.scalars().all()

    from datetime import datetime, timedelta, timezone
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    total = len(all_posts)
    published = [p for p in all_posts if p.status == PostStatus.PUBLISHED]
    scheduled = [p for p in all_posts if p.status == PostStatus.SCHEDULED]
    generated = [p for p in all_posts if p.status == PostStatus.GENERATED]
    draft = [p for p in all_posts if p.status == PostStatus.DRAFT]
    this_week = [
        p for p in published
        if p.published_at and p.published_at >= one_week_ago
    ]

    avg_seo = 0
    if published:
        seo_scores = [p.seo_score for p in published if p.seo_score]
        avg_seo = int(sum(seo_scores) / len(seo_scores)) if seo_scores else 0

    return {
        "total": total,
        "published": len(published),
        "scheduled": len(scheduled),
        "generated": len(generated),
        "draft": len(draft),
        "this_week": len(this_week),
        "avg_seo_score": avg_seo,
    }


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """특정 포스트 상세 조회"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")
    return post


@router.get("/{post_id}/content")
async def get_post_content(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """포스트 HTML 콘텐츠 조회"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content or "",
        "meta_description": post.meta_description,
        "seo_issues": [],
    }


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    updates: PostUpdate,
    db: AsyncSession = Depends(get_db),
):
    """포스트 정보 수정"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.flush()
    await db.refresh(post)
    return post


@router.post("/{post_id}/regenerate-image")
async def regenerate_thumbnail(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """포스트 썸네일 이미지 재생성"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")

    try:
        image_path = image_generator.generate_thumbnail(
            title=post.title or post.primary_keyword,
            keyword=post.primary_keyword,
            post_type=post.post_type,
        )
        post.featured_image_path = image_path
        await db.flush()

        return {
            "message": "썸네일 재생성 완료",
            "image_path": image_path,
            "image_url": image_generator.get_image_url(image_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"썸네일 생성 실패: {str(e)}")


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """포스트 삭제"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")

    await db.delete(post)
