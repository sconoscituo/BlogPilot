"""
블로그 포스트 모델
생성된 블로그 글과 발행 상태를 관리합니다.
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Integer, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PostStatus(str, PyEnum):
    """포스트 상태 열거형"""
    DRAFT = "draft"           # 초안
    GENERATED = "generated"   # AI 생성 완료
    SCHEDULED = "scheduled"   # 발행 예약됨
    PUBLISHED = "published"   # 발행 완료
    FAILED = "failed"         # 발행 실패


class PostType(str, PyEnum):
    """포스트 유형 열거형"""
    INFORMATIONAL = "informational"  # 정보성
    REVIEW = "review"                # 리뷰
    COMPARISON = "comparison"        # 비교
    LISTICLE = "listicle"            # 리스트형


class Post(Base):
    """블로그 포스트 모델"""
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 기본 정보
    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="포스트 제목")
    slug: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="URL 슬러그")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="HTML 콘텐츠")
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True, comment="요약/발췌")
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="SEO 메타 설명")

    # 키워드 정보
    primary_keyword: Mapped[str] = mapped_column(String(200), nullable=False, comment="주요 키워드")
    secondary_keywords: Mapped[str | None] = mapped_column(Text, nullable=True, comment="보조 키워드 (쉼표 구분)")
    keyword_density: Mapped[float | None] = mapped_column(nullable=True, comment="키워드 밀도 (%)")

    # SEO 점수
    seo_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="SEO 점수 (0-100)")
    readability_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="가독성 점수")
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="단어 수")

    # 포스트 유형 및 상태
    post_type: Mapped[str] = mapped_column(
        Enum(PostType), default=PostType.INFORMATIONAL, comment="포스트 유형"
    )
    status: Mapped[str] = mapped_column(
        Enum(PostStatus), default=PostStatus.DRAFT, comment="포스트 상태"
    )

    # 워드프레스 발행 정보
    wordpress_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="워드프레스 포스트 ID")
    wordpress_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="발행된 포스트 URL")
    featured_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="썸네일 이미지 경로")

    # 예상 성과 지표
    estimated_monthly_traffic: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="예상 월 트래픽")
    estimated_keyword_difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="키워드 난이도 (0-100)")

    # 템플릿 참조
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), nullable=True)

    # 발행/예약 일시
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="예약 발행 일시")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="실제 발행 일시")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="생성 일시")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="수정 일시"
    )

    # 오류 정보
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="오류 메시지")

    def __repr__(self) -> str:
        return f"<Post id={self.id} title='{self.title[:30]}' status={self.status}>"
