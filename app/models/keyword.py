"""
키워드 모델
리서치된 키워드와 관련 데이터를 저장합니다.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, Float, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Keyword(Base):
    """키워드 모델"""
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 키워드 기본 정보
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, index=True, comment="키워드")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="출처 (naver/google/manual)")

    # 검색량 및 트렌드
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="월 예상 검색량")
    trend_score: Mapped[float | None] = mapped_column(Float, nullable=True, comment="트렌드 점수 (0-100)")

    # 경쟁도 및 난이도
    difficulty_score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="키워드 난이도 (0-100)")
    competition_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="경쟁 수준 (low/medium/high)"
    )

    # 관련 키워드
    related_keywords: Mapped[str | None] = mapped_column(Text, nullable=True, comment="관련 키워드 (JSON 배열)")
    long_tail_keywords: Mapped[str | None] = mapped_column(Text, nullable=True, comment="롱테일 키워드 (JSON 배열)")

    # 사용자 정의 우선순위
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="우선순위 (높을수록 먼저 처리)")
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, comment="글 생성에 사용됨 여부")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 상태")

    # 메타 정보
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="메모")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Keyword id={self.id} keyword='{self.keyword}' difficulty={self.difficulty_score}>"
