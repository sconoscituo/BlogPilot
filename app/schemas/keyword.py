"""
키워드 Pydantic 스키마
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KeywordCreate(BaseModel):
    """키워드 생성 요청 스키마"""
    keyword: str = Field(..., min_length=1, max_length=200, description="키워드")
    source: Optional[str] = Field("manual", description="출처")
    priority: int = Field(0, ge=0, le=10, description="우선순위")
    notes: Optional[str] = None


class KeywordResearchRequest(BaseModel):
    """키워드 리서치 요청 스키마"""
    seed_keyword: str = Field(..., description="시드 키워드")
    sources: list[str] = Field(["google", "naver"], description="리서치 출처")
    max_results: int = Field(20, ge=1, le=50, description="최대 결과 수")


class KeywordResponse(BaseModel):
    """키워드 응답 스키마"""
    id: int
    keyword: str
    source: Optional[str]
    search_volume: Optional[int]
    trend_score: Optional[float]
    difficulty_score: Optional[int]
    competition_level: Optional[str]
    related_keywords: Optional[str]
    long_tail_keywords: Optional[str]
    priority: int
    is_used: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KeywordSuggestion(BaseModel):
    """키워드 제안 (DB 저장 없이 반환)"""
    keyword: str
    source: str
    estimated_difficulty: Optional[int] = None
    competition_level: Optional[str] = None
    is_long_tail: bool = False
