"""
포스트 Pydantic 스키마
API 요청/응답 데이터 검증 및 직렬화
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    """포스트 생성 요청 스키마"""
    primary_keyword: str = Field(..., description="주요 키워드", min_length=1, max_length=200)
    secondary_keywords: Optional[str] = Field(None, description="보조 키워드 (쉼표 구분)")
    post_type: str = Field("informational", description="포스트 유형")
    template_id: Optional[int] = Field(None, description="사용할 템플릿 ID")
    scheduled_at: Optional[datetime] = Field(None, description="예약 발행 일시")
    notes: Optional[str] = Field(None, description="메모")


class PostUpdate(BaseModel):
    """포스트 수정 요청 스키마"""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    meta_description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class PostResponse(BaseModel):
    """포스트 응답 스키마"""
    id: int
    title: Optional[str]
    primary_keyword: str
    secondary_keywords: Optional[str]
    post_type: str
    status: str
    seo_score: Optional[int]
    word_count: Optional[int]
    wordpress_post_id: Optional[int]
    wordpress_url: Optional[str]
    featured_image_path: Optional[str]
    estimated_monthly_traffic: Optional[int]
    estimated_keyword_difficulty: Optional[int]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostGenerateRequest(BaseModel):
    """AI 글 생성 요청 스키마"""
    primary_keyword: str = Field(..., description="주요 키워드")
    secondary_keywords: Optional[str] = Field(None, description="보조 키워드")
    post_type: str = Field("informational", description="포스트 유형")
    template_id: Optional[int] = Field(None, description="템플릿 ID")
    target_word_count: int = Field(2000, ge=500, le=5000, description="목표 단어 수")
    language: str = Field("ko", description="언어 코드")


class PostPublishRequest(BaseModel):
    """워드프레스 발행 요청 스키마"""
    post_id: int = Field(..., description="발행할 포스트 ID")
    wp_status: str = Field("publish", description="워드프레스 상태 (publish/draft/future)")
    wp_categories: Optional[list[int]] = Field(None, description="카테고리 ID 목록")
    wp_tags: Optional[list[str]] = Field(None, description="태그 목록")
    upload_image: bool = Field(True, description="썸네일 이미지 업로드 여부")
