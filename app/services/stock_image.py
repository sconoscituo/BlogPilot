"""
Unsplash 스톡 이미지 자동 삽입 서비스
Unsplash API를 통해 키워드 관련 이미지를 검색하고 글의 H2 섹션마다 이미지를 삽입합니다.
"""
import logging
import re
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_API_BASE = "https://api.unsplash.com"


class StockImageService:
    """Unsplash 스톡 이미지 서비스"""

    async def search_images(self, query: str, per_page: int = 5) -> list[dict]:
        """
        Unsplash에서 키워드 관련 이미지 검색

        Args:
            query: 검색 키워드
            per_page: 반환할 이미지 수

        Returns:
            이미지 URL, 설명, 출처 목록
        """
        access_key = settings.UNSPLASH_ACCESS_KEY
        if not access_key:
            logger.warning("Unsplash API 키가 설정되지 않았습니다. 플레이스홀더 이미지를 사용합니다.")
            return self._get_placeholder_images(query, per_page)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{UNSPLASH_API_BASE}/search/photos",
                    params={
                        "query": query,
                        "per_page": per_page,
                        "orientation": "landscape",
                        "content_filter": "high",
                    },
                    headers={"Authorization": f"Client-ID {access_key}"},
                )
                resp.raise_for_status()
                data = resp.json()

            images = []
            for item in data.get("results", []):
                images.append({
                    "url": item["urls"].get("regular", item["urls"].get("small", "")),
                    "thumb_url": item["urls"].get("thumb", ""),
                    "alt": item.get("alt_description") or item.get("description") or query,
                    "photographer": item["user"]["name"],
                    "photographer_url": item["user"]["links"]["html"],
                    "unsplash_url": item["links"]["html"],
                    "width": item.get("width", 1080),
                    "height": item.get("height", 720),
                })
            return images
        except Exception as e:
            logger.error(f"Unsplash 이미지 검색 실패: {e}")
            return self._get_placeholder_images(query, per_page)

    def _get_placeholder_images(self, query: str, count: int) -> list[dict]:
        """API 미설정 또는 오류 시 플레이스홀더 이미지 반환"""
        encoded = query.replace(" ", "+")
        return [
            {
                "url": f"https://via.placeholder.com/1200x630?text={encoded}",
                "thumb_url": f"https://via.placeholder.com/400x210?text={encoded}",
                "alt": f"{query} 관련 이미지",
                "photographer": "Placeholder",
                "photographer_url": "",
                "unsplash_url": "",
                "width": 1200,
                "height": 630,
            }
            for _ in range(count)
        ]

    def insert_images_into_content(
        self,
        content: str,
        primary_keyword: str,
        images: list[dict],
    ) -> str:
        """
        HTML 콘텐츠의 H2 섹션마다 이미지 자동 삽입

        Args:
            content: 원본 HTML 콘텐츠
            primary_keyword: 주요 키워드 (이미지 alt 태그에 활용)
            images: 삽입할 이미지 목록

        Returns:
            이미지가 삽입된 HTML 콘텐츠
        """
        if not images:
            return content

        # H2 태그 위치 찾기
        h2_pattern = re.compile(r"(<h2[^>]*>.*?</h2>)", re.IGNORECASE | re.DOTALL)
        h2_matches = list(h2_pattern.finditer(content))

        if not h2_matches:
            logger.info("H2 섹션이 없어 이미지 삽입을 건너뜁니다.")
            return content

        # 이미지 인덱스와 삽입 위치를 역순으로 처리 (인덱스 밀림 방지)
        # 최대 이미지 수만큼만 삽입 (첫 번째 H2는 글 상단에 이미 이미지가 있을 수 있어 건너뜀)
        insert_pairs = []
        img_idx = 0
        for match in h2_matches[1:]:  # 첫 번째 H2 이후부터 삽입
            if img_idx >= len(images):
                break
            insert_pairs.append((match.end(), images[img_idx]))
            img_idx += 1

        # 역순으로 삽입하여 위치 오프셋 유지
        result = content
        for insert_pos, img in reversed(insert_pairs):
            img_html = self._build_image_html(img, primary_keyword)
            result = result[:insert_pos] + "\n" + img_html + "\n" + result[insert_pos:]

        logger.info(f"총 {len(insert_pairs)}개 이미지 삽입 완료")
        return result

    def _build_image_html(self, img: dict, keyword: str) -> str:
        """이미지 HTML 마크업 생성 (Unsplash 출처 표기 포함)"""
        alt = img.get("alt") or f"{keyword} 이미지"
        url = img.get("url", "")
        photographer = img.get("photographer", "")
        photographer_url = img.get("photographer_url", "")
        unsplash_url = img.get("unsplash_url", "")

        # Unsplash 출처 표기 (API 이용약관 준수)
        if photographer and unsplash_url:
            credit = (
                f'<figcaption style="font-size:0.75rem;color:#6b7280;margin-top:4px;">'
                f'사진: <a href="{photographer_url}" target="_blank" rel="noopener">{photographer}</a> / '
                f'<a href="{unsplash_url}" target="_blank" rel="noopener">Unsplash</a>'
                f"</figcaption>"
            )
        else:
            credit = ""

        return (
            f'<figure style="margin:1.5rem 0;">'
            f'<img src="{url}" alt="{alt}" '
            f'style="width:100%;border-radius:8px;object-fit:cover;" loading="lazy">'
            f"{credit}"
            f"</figure>"
        )

    async def enrich_content_with_images(
        self,
        content: str,
        primary_keyword: str,
        max_images: int = 3,
    ) -> tuple[str, int]:
        """
        콘텐츠에 Unsplash 이미지를 검색하고 H2마다 자동 삽입하는 통합 메서드

        Args:
            content: 원본 HTML 콘텐츠
            primary_keyword: 주요 키워드
            max_images: 최대 삽입 이미지 수

        Returns:
            (이미지 삽입된 콘텐츠, 삽입된 이미지 수)
        """
        images = await self.search_images(primary_keyword, per_page=max_images)
        if not images:
            return content, 0

        updated = self.insert_images_into_content(content, primary_keyword, images[:max_images])
        inserted_count = min(len(images), max_images)
        return updated, inserted_count


# 전역 인스턴스
stock_image_service = StockImageService()
