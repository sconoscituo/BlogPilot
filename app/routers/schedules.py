"""
스케줄 관리 API 라우터
발행 예약 생성, 조회, 취소 엔드포인트
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schedule import Schedule
from app.models.post import Post, PostStatus
from app.services.scheduler import publish_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedules", tags=["스케줄"])


@router.get("/")
async def list_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """스케줄 목록 조회"""
    query = select(Schedule).order_by(Schedule.scheduled_time.asc())

    if status:
        query = query.where(Schedule.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    schedules = result.scalars().all()

    schedule_list = []
    for s in schedules:
        # 연결된 포스트 정보 조회
        post_info = None
        if s.post_id:
            post_result = await db.execute(select(Post).where(Post.id == s.post_id))
            post = post_result.scalar_one_or_none()
            if post:
                post_info = {
                    "id": post.id,
                    "title": post.title,
                    "primary_keyword": post.primary_keyword,
                    "status": post.status,
                }

        schedule_list.append({
            "id": s.id,
            "name": s.name,
            "scheduled_time": s.scheduled_time.isoformat(),
            "status": s.status,
            "is_recurring": s.is_recurring,
            "recurrence_pattern": s.recurrence_pattern,
            "is_active": s.is_active,
            "run_count": s.run_count,
            "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            "error_message": s.error_message,
            "post": post_info,
        })

    return schedule_list


@router.post("/", status_code=201)
async def create_schedule(
    post_id: int,
    scheduled_time: datetime,
    name: Optional[str] = None,
    is_recurring: bool = False,
    recurrence_pattern: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """포스트 발행 스케줄 생성"""
    # 포스트 확인
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="포스트를 찾을 수 없습니다.")

    if post.status == PostStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="이미 발행된 포스트입니다.")

    if scheduled_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="예약 시간은 현재 시간 이후여야 합니다.")

    # 스케줄 생성
    schedule = Schedule(
        post_id=post_id,
        name=name or f"{post.title or post.primary_keyword} 발행 예약",
        scheduled_time=scheduled_time,
        is_recurring=is_recurring,
        recurrence_pattern=recurrence_pattern,
        status="pending",
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)

    # 포스트 상태 업데이트
    post.status = PostStatus.SCHEDULED
    post.scheduled_at = scheduled_time

    # APScheduler에 Job 등록
    job_id = await publish_scheduler.schedule_post(
        post_id=post_id,
        scheduled_time=scheduled_time,
        schedule_id=schedule.id,
    )

    return {
        "message": "발행 예약 완료",
        "schedule_id": schedule.id,
        "job_id": job_id,
        "scheduled_time": scheduled_time.isoformat(),
        "post_title": post.title,
    }


@router.get("/calendar")
async def get_schedule_calendar(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """월별 스케줄 캘린더 데이터 반환"""
    from calendar import monthrange
    import calendar

    # 해당 월의 시작/끝 날짜
    _, last_day = monthrange(year, month)
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, last_day, 23, 59, 59)

    result = await db.execute(
        select(Schedule).where(
            Schedule.scheduled_time >= start_date,
            Schedule.scheduled_time <= end_date,
        )
    )
    schedules = result.scalars().all()

    # 날짜별로 그룹화
    calendar_data = {}
    for s in schedules:
        day = s.scheduled_time.day
        if day not in calendar_data:
            calendar_data[day] = []
        calendar_data[day].append({
            "id": s.id,
            "name": s.name,
            "time": s.scheduled_time.strftime("%H:%M"),
            "status": s.status,
        })

    return {
        "year": year,
        "month": month,
        "days": calendar_data,
        "total": len(schedules),
    }


@router.get("/jobs")
async def get_scheduled_jobs():
    """현재 APScheduler에 등록된 Job 목록"""
    jobs = publish_scheduler.get_scheduled_jobs()
    return {"jobs": jobs, "total": len(jobs)}


@router.delete("/{schedule_id}", status_code=204)
async def cancel_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """스케줄 취소"""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="스케줄을 찾을 수 없습니다.")

    schedule.status = "cancelled"
    schedule.is_active = False

    # 연결된 포스트 상태 복원
    if schedule.post_id:
        post_result = await db.execute(select(Post).where(Post.id == schedule.post_id))
        post = post_result.scalar_one_or_none()
        if post and post.status == PostStatus.SCHEDULED:
            post.status = PostStatus.GENERATED
            post.scheduled_at = None


@router.patch("/{schedule_id}/reschedule")
async def reschedule(
    schedule_id: int,
    new_time: datetime,
    db: AsyncSession = Depends(get_db),
):
    """스케줄 시간 변경"""
    if new_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="새 예약 시간은 현재 시간 이후여야 합니다.")

    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="스케줄을 찾을 수 없습니다.")

    schedule.scheduled_time = new_time
    schedule.status = "pending"

    # 포스트 예약 시간도 업데이트
    if schedule.post_id:
        post_result = await db.execute(select(Post).where(Post.id == schedule.post_id))
        post = post_result.scalar_one_or_none()
        if post:
            post.scheduled_at = new_time
            post.status = PostStatus.SCHEDULED

    # 새 Job 등록
    if schedule.post_id:
        await publish_scheduler.schedule_post(
            post_id=schedule.post_id,
            scheduled_time=new_time,
            schedule_id=schedule.id,
        )

    return {
        "message": "스케줄 변경 완료",
        "schedule_id": schedule_id,
        "new_time": new_time.isoformat(),
    }
