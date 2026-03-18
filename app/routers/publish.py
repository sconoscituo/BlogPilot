"""
WordPress 발행 API 라우터
포스트의 WordPress 발행 관련 엔드포인트
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.post import Post, PostStatus
from app.schemas.post import PostPublishRequest
from app.services.wordpress import wordpress_client
from app.services.image_generator import image_generator
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/publish", tags=["발행"])


@router.get("/test-connection")
async def test_wordpress_connection():
    """WordPress 연결 상태 테스트"""
    if not settings.is_wordpress_configured:
        return {
            "connected": False,
            "message": "WordPress 설정이 완료되지 않았습니다. .env 파일을 확인하세요.",
        }

    result = await wordpress_client.test_connection()
    return {
        "connected": result.get("success", False),
        "message": "연결 성공" if result.get("success") else result.get("error", "연결 실패"),
        "details": result,
    }


@router.post("/post")
async def publish_post(
    request: PostPublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    포스트를 WordPress에 즉시 발행

    Args:
        request: 발행 요청 정보
    """
    if not settings.is_wordpress_configured:
        raise HTTPException(
            status_code=400,
            detail="WordPress가 설정되지 않았습니다. .env 파일에 WordPress 설정을 입력하세요.",
        )

    # 포스트 조회
    result = await db.execute(select(Post).where(Post.id == request.post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")

    if post.status == PostStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="이미 발행된 포스트입니다.")

    if not post.content:
        raise HTTPException(status_code=400, detail="발행할 콘텐츠가 없습니다. 먼저 AI로 글을 생성하세요.")

    # 태그 ID 목록 처리
    tag_ids = []
    if request.wp_tags:
        for tag_name in request.wp_tags:
            tag_id = await wordpress_client.create_tag(tag_name)
            if tag_id:
                tag_ids.append(tag_id)

    # 대표 이미지 업로드
    featured_media_id = None
    if request.upload_image and post.featured_image_path:
        try:
            media_result = await wordpress_client.upload_media(
                post.featured_image_path,
                alt_text=post.primary_keyword,
            )
            featured_media_id = media_result.get("media_id")
        except Exception as e:
            logger.warning(f"이미지 업로드 실패 (발행은 계속): {e}")

    # WordPress 발행
    try:
        wp_result = await wordpress_client.create_post(
            title=post.title,
            content=post.content,
            status=request.wp_status,
            slug=post.slug,
            excerpt=post.meta_description,
            categories=request.wp_categories,
            tags=tag_ids if tag_ids else None,
            featured_media=featured_media_id,
        )

        # 발행 성공 처리
        from datetime import datetime, timezone
        post.status = PostStatus.PUBLISHED
        post.wordpress_post_id = wp_result.get("post_id")
        post.wordpress_url = wp_result.get("url")
        post.published_at = datetime.now(timezone.utc)
        post.error_message = None

        await db.flush()

        return {
            "success": True,
            "message": "WordPress 발행 완료",
            "post_id": post.id,
            "wordpress_post_id": wp_result.get("post_id"),
            "wordpress_url": wp_result.get("url"),
            "status": wp_result.get("status"),
        }

    except Exception as e:
        # 발행 실패 처리
        post.status = PostStatus.FAILED
        post.error_message = str(e)
        await db.flush()

        logger.error(f"발행 실패: {e}")
        raise HTTPException(status_code=500, detail=f"WordPress 발행 실패: {str(e)}")


@router.get("/categories")
async def get_wp_categories():
    """WordPress 카테고리 목록 조회"""
    if not settings.is_wordpress_configured:
        return []

    categories = await wordpress_client.get_categories()
    return [
        {"id": cat.get("id"), "name": cat.get("name"), "slug": cat.get("slug")}
        for cat in categories
    ]


@router.get("/tags")
async def get_wp_tags():
    """WordPress 태그 목록 조회"""
    if not settings.is_wordpress_configured:
        return []

    tags = await wordpress_client.get_tags()
    return [
        {"id": tag.get("id"), "name": tag.get("name"), "slug": tag.get("slug")}
        for tag in tags
    ]


@router.post("/retry/{post_id}")
async def retry_publish(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """실패한 포스트 발행 재시도"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")

    if post.status != PostStatus.FAILED:
        raise HTTPException(status_code=400, detail="실패 상태의 포스트만 재시도할 수 있습니다.")

    # 상태를 GENERATED로 변경하여 재발행 가능하게
    post.status = PostStatus.GENERATED
    post.error_message = None
    await db.flush()

    return {"message": "재시도 준비 완료. 발행 버튼을 다시 누르세요.", "post_id": post_id}
