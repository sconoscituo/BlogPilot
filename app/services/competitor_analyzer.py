"""
경쟁 블로그 분석 서비스
키워드로 구글 상위 결과를 분석하여 더 나은 글 전략을 제시합니다.
"""
import logging
import re
import asyncio
from typing import Optional
from urllib.parse import quote_plus, urlparse

import httpx

logger = logging.getLogger(__name__)

# 요청 헤더 (User-Agent 설정으로 차단 우회)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class CompetitorAnalyzer:
    """경쟁 블로그 분석 서비스"""

    MAX_RESULTS = 10  # 분석할 상위 결과 수
    FETCH_TIMEOUT = 10.0  # 개별 페이지 조회 타임아웃(초)

    async def get_top_results(self, keyword: str) -> list[dict]:
        """
        구글 검색 상위 결과 목록 스크래핑

        Args:
            keyword: 분석할 검색 키워드

        Returns:
            상위 결과의 URL, 제목, 메타설명 목록
        """
        try:
            query = quote_plus(keyword)
            url = f"https://www.google.com/search?q={query}&num={self.MAX_RESULTS}&hl=ko"

            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS, timeout=15.0, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            return self._parse_google_results(html)
        except Exception as e:
            logger.error(f"구글 검색 결과 조회 실패: {e}")
            return []

    def _parse_google_results(self, html: str) -> list[dict]:
        """구글 검색 결과 HTML에서 제목, URL, 메타설명 추출"""
        results = []

        # 검색 결과 블록 패턴 (구글 HTML 구조)
        block_pattern = re.compile(
            r'<div[^>]+class="[^"]*tF2Cxc[^"]*"[^>]*>(.*?)</div>\s*</div>',
            re.DOTALL,
        )
        title_pattern = re.compile(r"<h3[^>]*>(.*?)</h3>", re.DOTALL)
        url_pattern = re.compile(r'href="(https?://[^"]+)"')
        desc_pattern = re.compile(
            r'<div[^>]+class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>', re.DOTALL
        )

        for match in block_pattern.finditer(html):
            block = match.group(1)

            title_m = title_pattern.search(block)
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""

            url_m = url_pattern.search(block)
            url = url_m.group(1) if url_m else ""

            desc_m = desc_pattern.search(block)
            description = re.sub(r"<[^>]+>", "", desc_m.group(1)).strip() if desc_m else ""

            if title and url:
                domain = urlparse(url).netloc
                results.append({
                    "rank": len(results) + 1,
                    "title": title,
                    "url": url,
                    "domain": domain,
                    "description": description,
                })
            if len(results) >= self.MAX_RESULTS:
                break

        return results

    async def analyze_page(self, url: str) -> dict:
        """
        개별 페이지 상세 분석 (제목, 글 길이, H2 구조)

        Args:
            url: 분석할 페이지 URL

        Returns:
            페이지 분석 결과 딕셔너리
        """
        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS, timeout=self.FETCH_TIMEOUT, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            return self._parse_page_content(html, url)
        except Exception as e:
            logger.warning(f"페이지 분석 실패 ({url}): {e}")
            return {
                "url": url,
                "word_count": 0,
                "h2_list": [],
                "h3_list": [],
                "has_table": False,
                "has_images": False,
                "error": str(e),
            }

    def _parse_page_content(self, html: str, url: str) -> dict:
        """HTML 페이지에서 콘텐츠 구조 분석"""
        # H2 제목 목록
        h2_list = [
            re.sub(r"<[^>]+>", "", m).strip()
            for m in re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
        ]
        h3_list = [
            re.sub(r"<[^>]+>", "", m).strip()
            for m in re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.IGNORECASE | re.DOTALL)
        ]

        # 전체 텍스트 길이 (태그 제거)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        word_count = len(text)

        has_table = bool(re.search(r"<table", html, re.IGNORECASE))
        has_images = bool(re.search(r"<img[^>]+src", html, re.IGNORECASE))

        return {
            "url": url,
            "word_count": word_count,
            "h2_count": len(h2_list),
            "h3_count": len(h3_list),
            "h2_list": h2_list[:10],  # 최대 10개
            "h3_list": h3_list[:10],
            "has_table": has_table,
            "has_images": has_images,
        }

    async def analyze_competitors(self, keyword: str) -> dict:
        """
        키워드에 대한 경쟁 분석 전체 수행

        Args:
            keyword: 분석할 키워드

        Returns:
            상위 결과 분석 + 전략 제안 데이터
        """
        logger.info(f"경쟁 분석 시작: '{keyword}'")

        # 상위 결과 목록 조회
        top_results = await self.get_top_results(keyword)

        if not top_results:
            logger.warning("검색 결과를 가져오지 못했습니다. 데모 데이터를 반환합니다.")
            return self._get_demo_data(keyword)

        # 상위 5개 페이지 상세 분석 (병렬)
        tasks = [self.analyze_page(r["url"]) for r in top_results[:5]]
        page_details = await asyncio.gather(*tasks, return_exceptions=True)

        analyzed = []
        for i, result in enumerate(top_results):
            detail = page_details[i] if i < len(page_details) and not isinstance(page_details[i], Exception) else {}
            analyzed.append({**result, **detail})

        # 전략 제안 생성
        strategy = self._generate_strategy(keyword, analyzed)

        return {
            "keyword": keyword,
            "results": analyzed,
            "strategy": strategy,
            "total_analyzed": len(analyzed),
            "is_demo": False,
        }

    def _generate_strategy(self, keyword: str, results: list[dict]) -> dict:
        """경쟁 분석 결과를 바탕으로 전략 제안 생성"""
        if not results:
            return {}

        # 평균 글 길이
        word_counts = [r.get("word_count", 0) for r in results if r.get("word_count", 0) > 0]
        avg_word_count = int(sum(word_counts) / len(word_counts)) if word_counts else 0
        target_word_count = int(avg_word_count * 1.2)  # 경쟁자보다 20% 더 길게

        # 평균 H2 수
        h2_counts = [r.get("h2_count", 0) for r in results]
        avg_h2 = int(sum(h2_counts) / len(h2_counts)) if h2_counts else 0
        target_h2 = max(avg_h2 + 2, 5)

        # 테이블/이미지 사용 현황
        table_ratio = sum(1 for r in results if r.get("has_table")) / len(results) if results else 0
        image_ratio = sum(1 for r in results if r.get("has_images")) / len(results) if results else 0

        # H2 제목 수집 (아이디어)
        all_h2 = []
        for r in results:
            all_h2.extend(r.get("h2_list", []))

        suggestions = []
        if target_word_count > 1000:
            suggestions.append(f"글 길이를 최소 {target_word_count:,}자 이상으로 작성하여 경쟁자보다 풍부한 콘텐츠를 제공하세요.")
        if target_h2 > 0:
            suggestions.append(f"최소 {target_h2}개의 H2 소제목으로 체계적인 구조를 만드세요.")
        if table_ratio > 0.5:
            suggestions.append("경쟁자의 60% 이상이 비교 테이블을 사용합니다. 테이블을 포함하면 유리합니다.")
        if image_ratio > 0.7:
            suggestions.append("이미지를 적극 활용하세요. 상위 결과의 대부분이 이미지를 사용 중입니다.")

        suggestions.append(f"'{keyword}' 관련 FAQ 섹션을 추가하여 롱테일 키워드를 함께 공략하세요.")
        suggestions.append("E-E-A-T (경험, 전문성, 권위성, 신뢰성)를 강조하는 서술로 작성하세요.")

        return {
            "avg_word_count": avg_word_count,
            "target_word_count": target_word_count,
            "avg_h2_count": avg_h2,
            "target_h2_count": target_h2,
            "table_usage_ratio": round(table_ratio * 100, 0),
            "image_usage_ratio": round(image_ratio * 100, 0),
            "common_h2_topics": list(set(all_h2))[:10],
            "suggestions": suggestions,
        }

    def _get_demo_data(self, keyword: str) -> dict:
        """스크래핑 실패 시 데모 데이터 반환"""
        demo_results = [
            {
                "rank": 1,
                "title": f"{keyword} - 완벽 가이드 2024",
                "url": "https://example-blog1.com/guide",
                "domain": "example-blog1.com",
                "description": f"{keyword}에 대해 알아야 할 모든 것. 전문가가 직접 작성한 상세 가이드.",
                "word_count": 4200,
                "h2_count": 8,
                "h2_list": [f"{keyword}이란?", "주요 방법 5가지", "실전 팁", "자주 묻는 질문"],
                "has_table": True,
                "has_images": True,
            },
            {
                "rank": 2,
                "title": f"초보자를 위한 {keyword} 따라하기",
                "url": "https://example-blog2.com/beginner",
                "domain": "example-blog2.com",
                "description": f"처음 시작하는 분들을 위한 {keyword} 기초부터 실전까지.",
                "word_count": 3100,
                "h2_count": 6,
                "h2_list": ["시작하기 전 준비사항", "단계별 방법", "주의사항", "마무리"],
                "has_table": False,
                "has_images": True,
            },
            {
                "rank": 3,
                "title": f"{keyword} TOP 10 추천",
                "url": "https://example-blog3.com/top10",
                "domain": "example-blog3.com",
                "description": f"전문가가 엄선한 {keyword} 추천 목록.",
                "word_count": 2800,
                "h2_count": 12,
                "h2_list": ["선정 기준", "1위 추천", "2위 추천", "3위 추천", "종합 비교"],
                "has_table": True,
                "has_images": True,
            },
        ]

        strategy = self._generate_strategy(keyword, demo_results)

        return {
            "keyword": keyword,
            "results": demo_results,
            "strategy": strategy,
            "total_analyzed": len(demo_results),
            "is_demo": True,
        }


# 전역 인스턴스
competitor_analyzer = CompetitorAnalyzer()
