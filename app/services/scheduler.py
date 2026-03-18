"""
발행 스케줄러 서비스
APScheduler를 사용하여 예약된 시간에 자동으로 포스트를 발행합니다.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.post import Post, PostStatus
from app.models.schedule import Schedule

logger = logging.getLogger(__name__)


class PublishScheduler:
    """비동기 발행 스케줄러"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            timezone=settings.SCHEDULER_TIMEZONE
        )
        self._is_started = False

    def start(self):
        """스케줄러 시작"""
        if not self._is_started:
            self.scheduler.start()
            self._is_started = True
            logger.info("발행 스케줄러 시작됨")

            # 1분마다 대기 중인 스케줄 확인
            self.scheduler.add_job(
                self._check_pending_schedules,
                trigger=IntervalTrigger(minutes=1),
                id="check_pending_schedules",
                replace_existing=True,
            )

    def shutdown(self):
        """스케줄러 종료"""
        if self._is_started:
            self.scheduler.shutdown(wait=False)
            self._is_started = False
            logger.info("발행 스케줄러 종료됨")

    async def schedule_post(
        self,
        post_id: int,
        scheduled_time: datetime,
        schedule_id: Optional[int] = None,
    ) -> str:
        """
        포스트 발행 예약

        Args:
            post_id: 발행할 포스트 ID
            scheduled_time: 예약 발행 일시
            schedule_id: 스케줄 레코드 ID

        Returns:
            APScheduler Job ID
        """
        job_id = f"publish_post_{post_id}_{int(scheduled_time.timestamp())}"

        self.scheduler.add_job(
            self._publish_scheduled_post,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[post_id, schedule_id],
            id=job_id,
            replace_existing=True,
        )

        logger.info(f"포스트 #{post_id} 발행 예약: {scheduled_time} (Job ID: {job_id})")
        return job_id

    async def cancel_schedule(self, job_id: str) -> bool:
        """예약된 발행 취소"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"스케줄 취소: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"스케줄 취소 실패: {e}")
            return False

    async def _publish_scheduled_post(
        self, post_id: int, schedule_id: Optional[int] = None
    ):
        """예약 시간이 되면 실행되는 발행 함수"""
        logger.info(f"예약 발행 실행: 포스트 #{post_id}")

        async with AsyncSessionLocal() as db:
            try:
                # 포스트 조회
                result = await db.execute(select(Post).where(Post.id == post_id))
                post = result.scalar_one_or_none()

                if not post:
                    logger.error(f"포스트를 찾을 수 없음: #{post_id}")
                    return

                if post.status == PostStatus.PUBLISHED:
                    logger.info(f"포스트 #{post_id}는 이미 발행되었습니다.")
                    return

                # WordPress 발행
                from app.services.wordpress import wordpress_client
                from app.services.image_generator import image_generator

                # 대표 이미지 업로드 (있는 경우)
                featured_media_id = None
                if post.featured_image_path and settings.is_wordpress_configured:
                    try:
                        media_result = await wordpress_client.upload_media(
                            post.featured_image_path,
                            alt_text=post.primary_keyword,
                        )
                        featured_media_id = media_result.get("media_id")
                    except Exception as e:
                        logger.warning(f"이미지 업로드 실패 (발행은 계속): {e}")

                # 포스트 발행
                wp_result = await wordpress_client.create_post(
                    title=post.title,
                    content=post.content or "",
                    status="publish",
                    slug=post.slug,
                    excerpt=post.meta_description,
                    featured_media=featured_media_id,
                )

                # 발행 성공 처리
                await db.execute(
                    update(Post)
                    .where(Post.id == post_id)
                    .values(
                        status=PostStatus.PUBLISHED,
                        wordpress_post_id=wp_result.get("post_id"),
                        wordpress_url=wp_result.get("url"),
                        published_at=datetime.utcnow(),
                        error_message=None,
                    )
                )

                # 스케줄 완료 처리
                if schedule_id:
                    await db.execute(
                        update(Schedule)
                        .where(Schedule.id == schedule_id)
                        .values(
                            status="completed",
                            last_run_at=datetime.utcnow(),
                            run_count=Schedule.run_count + 1,
                        )
                    )

                await db.commit()
                logger.info(f"포스트 #{post_id} 발행 완료: {wp_result.get('url')}")

            except Exception as e:
                logger.error(f"예약 발행 실패: 포스트 #{post_id} - {e}")

                # 실패 상태 업데이트
                try:
                    await db.execute(
                        update(Post)
                        .where(Post.id == post_id)
                        .values(
                            status=PostStatus.FAILED,
                            error_message=str(e),
                        )
                    )
                    if schedule_id:
                        await db.execute(
                            update(Schedule)
                            .where(Schedule.id == schedule_id)
                            .values(
                                status="failed",
                                error_message=str(e),
                                last_run_at=datetime.utcnow(),
                            )
                        )
                    await db.commit()
                except Exception as db_error:
                    logger.error(f"오류 상태 업데이트 실패: {db_error}")

    async def _check_pending_schedules(self):
        """대기 중인 스케줄 주기적 확인 및 처리"""
        now = datetime.utcnow()

        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Schedule).where(
                        Schedule.status == "pending",
                        Schedule.is_active == True,
                        Schedule.scheduled_time <= now,
                    )
                )
                pending = result.scalars().all()

                for schedule in pending:
                    logger.info(f"대기 중인 스케줄 처리: #{schedule.id}")
                    if schedule.post_id:
                        await self._publish_scheduled_post(schedule.post_id, schedule.id)

            except Exception as e:
                logger.error(f"스케줄 확인 중 오류: {e}")

    def get_scheduled_jobs(self) -> list[dict]:
        """현재 예약된 Job 목록 반환"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs


# 전역 인스턴스
publish_scheduler = PublishScheduler()
