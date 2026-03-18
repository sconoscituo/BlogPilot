"""
자동 내부링크 삽입 서비스
기존 발행된 글 목록에서 키워드 매칭으로 관련 글을 찾아 내부링크를 자동 삽입합니다.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 내부링크를 삽입하지 않을 태그 내부 패턴
_TAG_CONTENT_RE = re.compile(r"<(a|h1|h2|h3|h4|h5|h6)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


class InternalLinker:
    """자동 내부링크 삽입 서비스"""

    MAX_LINKS = 3  # 글당 최대 내부링크 수

    async def get_published_posts(self, db) -> list[dict]:
        """
        발행된 포스트 목록 조회

        Args:
            db: 데이터베이스 세션

        Returns:
            발행된 포스트의 제목, 슬러그, 키워드 목록
        """
        try:
            from sqlalchemy import select
            from app.models.post import Post, PostStatus

            result = await db.execute(
                select(Post.id, Post.title, Post.slug, Post.primary_keyword, Post.secondary_keywords, Post.wordpress_url)
                .where(Post.status == PostStatus.PUBLISHED)
                .order_by(Post.published_at.desc())
                .limit(200)
            )
            rows = result.fetchall()
            posts = []
            for row in rows:
                posts.append({
                    "id": row.id,
                    "title": row.title or "",
                    "slug": row.slug or "",
                    "primary_keyword": row.primary_keyword or "",
                    "secondary_keywords": row.secondary_keywords or "",
                    "wordpress_url": row.wordpress_url or f"/{row.slug}",
                })
            return posts
        except Exception as e:
            logger.error(f"발행된 포스트 목록 조회 실패: {e}")
            return []

    def find_related_posts(
        self,
        content: str,
        primary_keyword: str,
        published_posts: list[dict],
        current_post_id: Optional[int] = None,
    ) -> list[dict]:
        """
        현재 글과 관련된 포스트 찾기 (키워드 매칭 방식)

        Args:
            content: 현재 글의 HTML 콘텐츠
            primary_keyword: 현재 글의 주요 키워드
            published_posts: 발행된 포스트 목록
            current_post_id: 현재 포스트 ID (자기 자신 제외용)

        Returns:
            관련도 순으로 정렬된 포스트 목록 (최대 MAX_LINKS개)
        """
        content_lower = content.lower()
        scored = []

        for post in published_posts:
            # 자기 자신 제외
            if current_post_id and post["id"] == current_post_id:
                continue

            score = 0
            post_kw = post["primary_keyword"].lower()
            post_title = post["title"].lower()

            # 현재 글 본문에 대상 포스트의 키워드가 등장하면 점수 부여
            if post_kw and post_kw in content_lower:
                score += 3

            # 현재 글의 키워드가 대상 포스트 제목에 포함되면 점수 부여
            if primary_keyword.lower() in post_title:
                score += 2

            # 보조 키워드 매칭
            secondary = post.get("secondary_keywords", "")
            if secondary:
                for kw in secondary.split(","):
                    kw = kw.strip().lower()
                    if kw and kw in content_lower:
                        score += 1

            if score > 0:
                scored.append({"post": post, "score": score})

        # 관련도 순 정렬 후 상위 MAX_LINKS개 반환
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [item["post"] for item in scored[: self.MAX_LINKS]]

    def insert_internal_links(
        self,
        content: str,
        related_posts: list[dict],
    ) -> str:
        """
        HTML 콘텐츠에 내부링크 삽입

        Args:
            content: 원본 HTML 콘텐츠
            related_posts: 삽입할 관련 포스트 목록

        Returns:
            내부링크가 삽입된 HTML 콘텐츠
        """
        if not related_posts:
            return content

        inserted_count = 0
        modified = content

        for post in related_posts:
            if inserted_count >= self.MAX_LINKS:
                break

            keyword = post["primary_keyword"]
            url = post["wordpress_url"] if post["wordpress_url"].startswith("http") else f"/{post['slug']}"
            title = post["title"]

            if not keyword:
                continue

            # 태그 내부가 아닌 일반 텍스트에서 첫 번째 키워드 등장 위치에 링크 삽입
            # 이미 링크가 걸려 있는 텍스트는 건드리지 않음
            pattern = re.compile(
                rf"(?<!<a[^>]*>)(?<!</a>)({re.escape(keyword)})(?![^<]*</a>)",
                re.IGNORECASE,
            )

            # 첫 번째 매칭만 링크로 교체
            new_content, n = pattern.subn(
                rf'<a href="{url}" title="{title}">\1</a>',
                modified,
                count=1,
            )
            if n > 0:
                modified = new_content
                inserted_count += 1
                logger.debug(f"내부링크 삽입: '{keyword}' -> {url}")

        if inserted_count > 0:
            logger.info(f"총 {inserted_count}개 내부링크 삽입 완료")

        return modified

    async def process_content(
        self,
        content: str,
        primary_keyword: str,
        db,
        current_post_id: Optional[int] = None,
    ) -> tuple[str, int]:
        """
        글 콘텐츠에 내부링크를 자동 삽입하는 통합 메서드

        Args:
            content: 원본 HTML 콘텐츠
            primary_keyword: 주요 키워드
            db: 데이터베이스 세션
            current_post_id: 현재 포스트 ID

        Returns:
            (내부링크 삽입된 콘텐츠, 삽입된 링크 수)
        """
        published_posts = await self.get_published_posts(db)
        if not published_posts:
            logger.info("발행된 포스트가 없어 내부링크를 건너뜁니다.")
            return content, 0

        related = self.find_related_posts(content, primary_keyword, published_posts, current_post_id)
        if not related:
            logger.info("관련 포스트를 찾지 못해 내부링크를 건너뜁니다.")
            return content, 0

        updated = self.insert_internal_links(content, related)
        link_count = len(related)
        return updated, link_count


# 전역 인스턴스
internal_linker = InternalLinker()
