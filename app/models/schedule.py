"""
발행 스케줄 모델
자동 발행 일정을 관리합니다.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Schedule(Base):
    """발행 스케줄 모델"""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 포스트 연결
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True, comment="연결된 포스트 ID")

    # 스케줄 설정
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="스케줄 이름")
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="예약 발행 일시")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Seoul", comment="타임존")

    # 반복 설정
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, comment="반복 스케줄 여부")
    recurrence_pattern: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="반복 패턴 (daily/weekly/monthly)"
    )
    recurrence_interval: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="반복 간격")

    # 자동 생성 설정
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False, comment="자동 글 생성 여부")
    keyword_id: Mapped[int | None] = mapped_column(ForeignKey("keywords.id"), nullable=True, comment="자동 생성 시 사용할 키워드")
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), nullable=True, comment="자동 생성 시 사용할 템플릿")

    # 상태
    status: Mapped[str] = mapped_column(
        String(50), default="pending", comment="상태 (pending/running/completed/failed/cancelled)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="활성 여부")

    # 실행 결과
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="마지막 실행 일시")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="다음 실행 예정 일시")
    run_count: Mapped[int] = mapped_column(Integer, default=0, comment="실행 횟수")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="오류 메시지")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="메모")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Schedule id={self.id} name='{self.name}' status={self.status}>"
