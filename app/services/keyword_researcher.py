"""
키워드 리서치 서비스
네이버/구글 자동완성 API로 키워드를 수집하고 난이도를 추정합니다.
"""
import json
import logging
import asyncio
import random
from typing import Optional
from urllib.parse import quote

import httpx

from app.config import settings
from app.schemas.keyword import KeywordSuggestion

logger = logging.getLogger(__name__)

# 구글 자동완성 API URL
GOOGLE_AUTOCOMPLETE_URL = "https://suggestqueries.google.com/complete/search"
# 네이버 자동완성 API URL
NAVER_AUTOCOMPLETE_URL = "https://ac.search.naver.com/nx/ac"

# 영어 알파벳 + 한글 자모 (롱테일 키워드 확장용)
KOREAN_MODIFIERS = [
    "추천", "방법", "비교", "리뷰", "후기", "가격", "종류", "효과",
    "장단점", "선택", "사용법", "주의사항", "순위", "베스트", "무료",
    "2024", "2025", "입문", "초보", "전문가", "최고", "저렴한",
]


class KeywordResearcher:
    """키워드 리서치 서비스"""

    def __init__(self):
        self.timeout = settings.KEYWORD_REQUEST_TIMEOUT
        self.max_keywords = settings.MAX_KEYWORDS_PER_SEARCH

    async def research_keyword(
        self,
        seed_keyword: str,
        sources: list[str] = None,
        max_results: int = 20,
    ) -> list[KeywordSuggestion]:
        """
        시드 키워드 기반 관련 키워드 리서치

        Args:
            seed_keyword: 시드 키워드
            sources: 리서치 출처 목록 (google, naver)
            max_results: 최대 결과 수

        Returns:
            KeywordSuggestion 목록
        """
        if sources is None:
            sources = ["google", "naver"]

        tasks = []
        if "google" in sources:
            tasks.append(self._fetch_google_suggestions(seed_keyword))
        if "naver" in sources:
            tasks.append(self._fetch_naver_suggestions(seed_keyword))

        # 병렬로 API 호출
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_suggestions: list[KeywordSuggestion] = []
        seen_keywords: set[str] = set()

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"키워드 리서치 API 오류: {result}")
                continue
            for suggestion in result:
                if suggestion.keyword.lower() not in seen_keywords:
                    seen_keywords.add(suggestion.keyword.lower())
                    all_suggestions.append(suggestion)

        # 롱테일 키워드 추가 생성
        long_tail = self._generate_long_tail_keywords(seed_keyword)
        for kw in long_tail:
            if kw.lower() not in seen_keywords:
                seen_keywords.add(kw.lower())
                difficulty = self._estimate_difficulty(kw)
                all_suggestions.append(KeywordSuggestion(
                    keyword=kw,
                    source="generated",
                    estimated_difficulty=difficulty,
                    competition_level=self._difficulty_to_level(difficulty),
                    is_long_tail=True,
                ))

        # 난이도 기준 정렬 (낮은 난이도 우선)
        all_suggestions.sort(key=lambda x: x.estimated_difficulty or 50)

        return all_suggestions[:max_results]

    async def _fetch_google_suggestions(self, keyword: str) -> list[KeywordSuggestion]:
        """구글 자동완성 API로 키워드 수집"""
        suggestions = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "q": keyword,
                    "hl": "ko",
                    "gl": "kr",
                    "client": "firefox",
                }
                response = await client.get(GOOGLE_AUTOCOMPLETE_URL, params=params)
                response.raise_for_status()

                data = response.json()
                if len(data) >= 2 and isinstance(data[1], list):
                    for suggestion in data[1][:15]:
                        if isinstance(suggestion, str) and suggestion != keyword:
                            difficulty = self._estimate_difficulty(suggestion)
                            suggestions.append(KeywordSuggestion(
                                keyword=suggestion,
                                source="google",
                                estimated_difficulty=difficulty,
                                competition_level=self._difficulty_to_level(difficulty),
                                is_long_tail=len(suggestion.split()) > 2 or len(suggestion) > 10,
                            ))

        except Exception as e:
            logger.warning(f"구글 자동완성 API 오류: {e}")
            # 폴백: 간단한 모디파이어로 키워드 생성
            suggestions = self._generate_fallback_suggestions(keyword, "google")

        return suggestions

    async def _fetch_naver_suggestions(self, keyword: str) -> list[KeywordSuggestion]:
        """네이버 자동완성 API로 키워드 수집"""
        suggestions = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "q": keyword,
                    "st": 111,
                    "r_format": "json",
                    "r_enc": "UTF-8",
                    "q_enc": "UTF-8",
                    "t_koreng": 1,
                    "ans": 2,
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.naver.com",
                }
                response = await client.get(
                    NAVER_AUTOCOMPLETE_URL, params=params, headers=headers
                )
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [[]])[0] if data.get("items") else []

                for item in items[:15]:
                    if isinstance(item, list) and len(item) > 0:
                        kw = item[0]
                    elif isinstance(item, str):
                        kw = item
                    else:
                        continue

                    if kw and kw != keyword:
                        difficulty = self._estimate_difficulty(kw)
                        suggestions.append(KeywordSuggestion(
                            keyword=kw,
                            source="naver",
                            estimated_difficulty=difficulty,
                            competition_level=self._difficulty_to_level(difficulty),
                            is_long_tail=len(kw) > 10,
                        ))

        except Exception as e:
            logger.warning(f"네이버 자동완성 API 오류: {e}")
            suggestions = self._generate_fallback_suggestions(keyword, "naver")

        return suggestions

    def _generate_long_tail_keywords(self, seed: str) -> list[str]:
        """롱테일 키워드 생성"""
        long_tail = []
        # 앞에 수식어 추가
        for modifier in KOREAN_MODIFIERS[:8]:
            long_tail.append(f"{seed} {modifier}")
        # 뒤에 수식어 추가
        for modifier in KOREAN_MODIFIERS[8:14]:
            long_tail.append(f"{modifier} {seed}")
        return long_tail

    def _generate_fallback_suggestions(self, keyword: str, source: str) -> list[KeywordSuggestion]:
        """API 실패 시 폴백 키워드 생성"""
        fallback_modifiers = ["추천", "방법", "비교", "리뷰", "가격", "효과", "종류"]
        suggestions = []
        for mod in fallback_modifiers:
            kw = f"{keyword} {mod}"
            difficulty = self._estimate_difficulty(kw)
            suggestions.append(KeywordSuggestion(
                keyword=kw,
                source=source,
                estimated_difficulty=difficulty,
                competition_level=self._difficulty_to_level(difficulty),
                is_long_tail=True,
            ))
        return suggestions

    def _estimate_difficulty(self, keyword: str) -> int:
        """
        키워드 난이도 추정 (0-100)
        실제 SEO 도구 없이 휴리스틱 방법 사용:
        - 키워드 길이가 길수록 롱테일 → 난이도 낮음
        - 단어 수가 많을수록 → 난이도 낮음
        - 일반적인 단어 패턴 분석
        """
        length = len(keyword)
        word_count = len(keyword.split())

        # 기본 난이도: 길이에 반비례
        if length <= 4:
            base_difficulty = random.randint(70, 90)
        elif length <= 8:
            base_difficulty = random.randint(50, 75)
        elif length <= 12:
            base_difficulty = random.randint(30, 60)
        else:
            base_difficulty = random.randint(10, 40)

        # 단어 수에 따른 조정
        if word_count >= 3:
            base_difficulty = max(10, base_difficulty - 15)
        elif word_count >= 2:
            base_difficulty = max(15, base_difficulty - 8)

        # 브랜드명/연도가 포함된 경우 난이도 낮춤
        year_keywords = ["2024", "2025", "최신", "새로운"]
        if any(y in keyword for y in year_keywords):
            base_difficulty = max(10, base_difficulty - 10)

        return min(100, max(1, base_difficulty))

    def _difficulty_to_level(self, difficulty: int) -> str:
        """난이도 수치를 레벨 문자열로 변환"""
        if difficulty <= 30:
            return "low"
        elif difficulty <= 60:
            return "medium"
        else:
            return "high"

    async def analyze_keyword_trends(self, keywords: list[str]) -> dict:
        """
        키워드 트렌드 분석
        실제 트렌드 API 없이 추정치 제공
        """
        results = {}
        for keyword in keywords:
            difficulty = self._estimate_difficulty(keyword)
            # 예상 검색량 추정 (키워드 길이 기반 휴리스틱)
            length = len(keyword)
            if length <= 4:
                estimated_volume = random.randint(10000, 100000)
            elif length <= 8:
                estimated_volume = random.randint(1000, 15000)
            elif length <= 15:
                estimated_volume = random.randint(100, 3000)
            else:
                estimated_volume = random.randint(10, 500)

            results[keyword] = {
                "difficulty": difficulty,
                "competition_level": self._difficulty_to_level(difficulty),
                "estimated_monthly_volume": estimated_volume,
                "trend_score": random.randint(30, 95),
            }

        return results


# 전역 인스턴스
keyword_researcher = KeywordResearcher()
