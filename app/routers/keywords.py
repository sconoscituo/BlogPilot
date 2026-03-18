"""
키워드 리서치 API 라우터
키워드 조회, 리서치, 관리 엔드포인트
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.keyword import Keyword
from app.schemas.keyword import KeywordCreate, KeywordResearchRequest, KeywordResponse, KeywordSuggestion
from app.services.keyword_researcher import keyword_researcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/keywords", tags=["키워드"])


@router.get("/", response_model=list[KeywordResponse])
async def list_keywords(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = Query(None),
    is_used: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """저장된 키워드 목록 조회"""
    query = select(Keyword).order_by(Keyword.priority.desc(), Keyword.created_at.desc())

    if is_active is not None:
        query = query.where(Keyword.is_active == is_active)
    if is_used is not None:
        query = query.where(Keyword.is_used == is_used)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=KeywordResponse, status_code=201)
async def create_keyword(
    keyword_data: KeywordCreate,
    db: AsyncSession = Depends(get_db),
):
    """키워드 수동 추가"""
    # 중복 확인
    existing = await db.execute(
        select(Keyword).where(Keyword.keyword == keyword_data.keyword)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 키워드입니다.")

    keyword = Keyword(
        keyword=keyword_data.keyword,
        source=keyword_data.source or "manual",
        priority=keyword_data.priority,
        notes=keyword_data.notes,
    )
    db.add(keyword)
    await db.flush()
    await db.refresh(keyword)
    return keyword


@router.post("/research", response_model=list[KeywordSuggestion])
async def research_keywords(
    request: KeywordResearchRequest,
):
    """
    키워드 리서치 실행 (DB 저장 없이 결과만 반환)
    네이버/구글 자동완성 API로 관련 키워드 수집
    """
    try:
        suggestions = await keyword_researcher.research_keyword(
            seed_keyword=request.seed_keyword,
            sources=request.sources,
            max_results=request.max_results,
        )
        return suggestions
    except Exception as e:
        logger.error(f"키워드 리서치 오류: {e}")
        raise HTTPException(status_code=500, detail=f"키워드 리서치 실패: {str(e)}")


@router.post("/research/save")
async def research_and_save_keywords(
    request: KeywordResearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """키워드 리서치 후 DB에 저장"""
    suggestions = await keyword_researcher.research_keyword(
        seed_keyword=request.seed_keyword,
        sources=request.sources,
        max_results=request.max_results,
    )

    saved_count = 0
    skipped_count = 0

    for suggestion in suggestions:
        # 중복 확인
        existing = await db.execute(
            select(Keyword).where(Keyword.keyword == suggestion.keyword)
        )
        if existing.scalar_one_or_none():
            skipped_count += 1
            continue

        keyword = Keyword(
            keyword=suggestion.keyword,
            source=suggestion.source,
            difficulty_score=suggestion.estimated_difficulty,
            competition_level=suggestion.competition_level,
        )
        db.add(keyword)
        saved_count += 1

    await db.flush()

    return {
        "message": f"{saved_count}개 키워드 저장 완료 ({skipped_count}개 중복 건너뜀)",
        "saved": saved_count,
        "skipped": skipped_count,
        "total": len(suggestions),
    }


@router.post("/analyze")
async def analyze_keyword_trends(
    keywords: list[str],
):
    """키워드 트렌드 분석"""
    if not keywords:
        raise HTTPException(status_code=400, detail="분석할 키워드를 입력하세요.")
    if len(keywords) > 20:
        raise HTTPException(status_code=400, detail="한 번에 최대 20개 키워드만 분석 가능합니다.")

    results = await keyword_researcher.analyze_keyword_trends(keywords)
    return results


@router.get("/stats/summary")
async def get_keyword_stats(db: AsyncSession = Depends(get_db)):
    """키워드 통계 요약"""
    total = await db.execute(select(Keyword))
    all_kw = total.scalars().all()

    used = [k for k in all_kw if k.is_used]
    active = [k for k in all_kw if k.is_active]
    low_difficulty = [k for k in all_kw if k.difficulty_score and k.difficulty_score <= 30]

    return {
        "total": len(all_kw),
        "active": len(active),
        "used": len(used),
        "unused": len(active) - len(used),
        "low_difficulty": len(low_difficulty),
    }


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(
    keyword_id: int,
    db: AsyncSession = Depends(get_db),
):
    """특정 키워드 상세 조회"""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")
    return keyword


@router.patch("/{keyword_id}")
async def update_keyword(
    keyword_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
):
    """키워드 정보 수정"""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")

    allowed_fields = {"priority", "is_active", "is_used", "notes"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(keyword, field, value)

    await db.flush()
    return {"message": "키워드 업데이트 완료"}


@router.delete("/{keyword_id}", status_code=204)
async def delete_keyword(
    keyword_id: int,
    db: AsyncSession = Depends(get_db),
):
    """키워드 삭제"""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()
    if not keyword:
        raise HTTPException(status_code=404, detail="키워드를 찾을 수 없습니다.")

    await db.delete(keyword)
