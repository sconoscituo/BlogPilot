"""
AI 콘텐츠 생성 서비스
Gemini API를 사용하여 SEO 최적화된 블로그 글을 생성합니다.
"""
import logging
import re
from typing import Optional

from app.services.gemini import gemini_client
from app.services.seo_optimizer import seo_optimizer

logger = logging.getLogger(__name__)

# 포스트 유형별 시스템 프롬프트
SYSTEM_PROMPTS = {
    "informational": """당신은 한국어 SEO 전문 블로그 작가입니다.
SEO 최적화된 정보성 블로그 포스트를 작성합니다.
다음 규칙을 엄격히 따르세요:
1. HTML 형식으로 작성 (h1, h2, h3, p, ul, ol, strong 태그 사용)
2. 주요 키워드를 제목, 첫 단락, 소제목에 자연스럽게 포함
3. 키워드 밀도 1.5-2% 유지
4. 독자에게 실질적인 가치 제공
5. 명확하고 구조화된 콘텐츠 작성
6. FAQ 섹션 포함
7. CTA(행동 촉구) 섹션으로 마무리""",

    "review": """당신은 한국어 제품/서비스 리뷰 전문 블로그 작가입니다.
신뢰성 있는 리뷰 포스트를 HTML 형식으로 작성합니다.
다음 규칙을 따르세요:
1. 장단점을 균형 있게 제시
2. 별점/점수 포함 (HTML 테이블 활용)
3. 실사용 경험 기반 서술
4. 주요 키워드를 자연스럽게 포함
5. 구매 결정을 돕는 명확한 결론
6. CTA 섹션 포함""",

    "comparison": """당신은 한국어 제품 비교 전문 블로그 작가입니다.
상세한 비교 분석 포스트를 HTML 형식으로 작성합니다.
다음 규칙을 따르세요:
1. 비교 테이블 반드시 포함 (HTML table 태그)
2. 각 항목의 장단점 명확히 구분
3. 추천 대상별 결론 제시
4. 주요 키워드를 자연스럽게 포함
5. 최종 추천으로 마무리""",

    "listicle": """당신은 한국어 리스트형 블로그 작가입니다.
유용한 리스트 포스트를 HTML 형식으로 작성합니다.
다음 규칙을 따르세요:
1. 번호 매긴 목록 또는 불릿 리스트 형식
2. 각 항목에 충분한 설명 추가
3. 실용적이고 즉시 적용 가능한 정보
4. 주요 키워드를 자연스럽게 포함
5. 요약 및 CTA로 마무리""",
}

# 포스트 유형별 프롬프트 템플릿
PROMPT_TEMPLATES = {
    "informational": """다음 키워드에 대한 SEO 최적화 정보성 블로그 포스트를 작성해주세요.

주요 키워드: {primary_keyword}
보조 키워드: {secondary_keywords}
목표 단어 수: {target_word_count}자 이상

필수 포함 요소:
1. <h1>으로 시작하는 SEO 최적화 제목 (키워드 포함, 50-60자)
2. 첫 단락에 키워드 자연스럽게 포함 (150자 이상)
3. 최소 4개의 <h2> 소제목 (일부에 키워드 포함)
4. 각 소제목 아래 상세 내용 (최소 200자)
5. 중간에 <h3> 소제목으로 세부 내용
6. 관련 내부 링크 플레이스홀더: <a href="/관련-포스트">관련 포스트 제목</a>
7. 이미지 대체 텍스트 포함: <img src="placeholder.jpg" alt="{primary_keyword} 관련 이미지">
8. FAQ 섹션 (3-5개 질문/답변)
9. 마지막에 CTA 섹션

메타 설명도 별도로 작성해주세요:
META_DESCRIPTION: [키워드 포함, 120-160자의 매력적인 설명]

HTML 형식으로만 작성하세요. 마크다운 사용 금지.""",

    "review": """다음 제품/서비스에 대한 SEO 최적화 리뷰 포스트를 작성해주세요.

리뷰 대상: {primary_keyword}
보조 키워드: {secondary_keywords}
목표 단어 수: {target_word_count}자 이상

필수 포함 요소:
1. <h1>으로 시작하는 제목 (리뷰/후기 키워드 포함, 50-60자)
2. 총점 평가 (별점 5점 만점)
3. 장점/단점 리스트
4. 상세 평가 섹션들 (디자인, 성능, 가격 등)
5. HTML 테이블로 스펙 정보
6. 최종 추천 여부와 추천 대상
7. CTA 섹션

메타 설명:
META_DESCRIPTION: [리뷰/후기 키워드 포함, 120-160자]

HTML 형식으로만 작성하세요.""",

    "comparison": """다음 주제에 대한 SEO 최적화 비교 포스트를 작성해주세요.

비교 주제: {primary_keyword}
보조 키워드: {secondary_keywords}
목표 단어 수: {target_word_count}자 이상

필수 포함 요소:
1. <h1>으로 시작하는 제목 (비교/vs 키워드 포함)
2. 비교 요약 테이블 (HTML table 태그)
3. 각 항목별 상세 분석
4. 가격 비교
5. 추천 대상별 결론 (초보자용/전문가용 등)
6. 최종 추천
7. CTA 섹션

메타 설명:
META_DESCRIPTION: [비교 키워드 포함, 120-160자]

HTML 형식으로만 작성하세요.""",

    "listicle": """다음 주제에 대한 SEO 최적화 리스트형 포스트를 작성해주세요.

주제: {primary_keyword}
보조 키워드: {secondary_keywords}
목표 단어 수: {target_word_count}자 이상

필수 포함 요소:
1. <h1>으로 시작하는 제목 (숫자 포함 - 예: "TOP 10", "7가지" 등)
2. 도입부 (왜 이 리스트가 필요한지)
3. 각 항목은 <h2>로 번호와 함께 제목
4. 각 항목마다 200자 이상의 설명
5. 각 항목의 핵심 포인트를 <ul>로 정리
6. 마지막에 요약 및 CTA

메타 설명:
META_DESCRIPTION: [숫자+키워드 포함, 120-160자]

HTML 형식으로만 작성하세요.""",
}


class ContentGenerator:
    """AI 블로그 콘텐츠 생성 서비스"""

    async def generate_post(
        self,
        primary_keyword: str,
        secondary_keywords: str = "",
        post_type: str = "informational",
        target_word_count: int = 2000,
        custom_system_prompt: Optional[str] = None,
        custom_user_prompt: Optional[str] = None,
    ) -> dict:
        """
        AI 블로그 포스트 생성

        Args:
            primary_keyword: 주요 키워드
            secondary_keywords: 보조 키워드 (쉼표 구분)
            post_type: 포스트 유형
            target_word_count: 목표 단어 수
            custom_system_prompt: 커스텀 시스템 프롬프트
            custom_user_prompt: 커스텀 사용자 프롬프트

        Returns:
            생성된 포스트 데이터 딕셔너리
        """
        logger.info(f"포스트 생성 시작: '{primary_keyword}' ({post_type})")

        # 프롬프트 선택
        system_prompt = custom_system_prompt or SYSTEM_PROMPTS.get(post_type, SYSTEM_PROMPTS["informational"])
        user_prompt_template = custom_user_prompt or PROMPT_TEMPLATES.get(post_type, PROMPT_TEMPLATES["informational"])

        # 프롬프트 변수 치환
        user_prompt = user_prompt_template.format(
            primary_keyword=primary_keyword,
            secondary_keywords=secondary_keywords or "없음",
            target_word_count=target_word_count,
        )

        # Gemini로 콘텐츠 생성
        raw_content = await gemini_client.generate_content(user_prompt, system_prompt)

        if not raw_content:
            raise ValueError("AI가 콘텐츠를 생성하지 못했습니다.")

        # 메타 설명 분리
        meta_description = self._extract_meta_description(raw_content)
        html_content = self._clean_content(raw_content)

        # 제목 추출
        title = self._extract_title(html_content) or f"{primary_keyword} - 완벽 가이드"

        # SEO 슬러그 생성
        slug = seo_optimizer.generate_slug(primary_keyword)

        # SEO 분석
        seo_results = seo_optimizer.analyze_content(
            content=html_content,
            title=title,
            primary_keyword=primary_keyword,
            meta_description=meta_description,
        )

        logger.info(f"포스트 생성 완료: '{title}' (SEO 점수: {seo_results['seo_score']})")

        return {
            "title": title,
            "slug": slug,
            "content": html_content,
            "meta_description": meta_description,
            "primary_keyword": primary_keyword,
            "secondary_keywords": secondary_keywords,
            "seo_score": seo_results["seo_score"],
            "word_count": seo_results["word_count"],
            "keyword_density": seo_results["keyword_density"],
            "readability_score": seo_results["readability_score"],
            "seo_issues": seo_results["issues"],
            "seo_suggestions": seo_results["suggestions"],
        }

    def _extract_meta_description(self, content: str) -> str:
        """콘텐츠에서 메타 설명 추출"""
        match = re.search(r"META_DESCRIPTION:\s*\[?([^\]\n]+)\]?", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _clean_content(self, content: str) -> str:
        """생성된 콘텐츠에서 메타 설명 제거 및 정리"""
        # 메타 설명 라인 제거
        content = re.sub(r"META_DESCRIPTION:.*?\n", "", content, flags=re.IGNORECASE)
        # 마크다운 코드 블록 제거
        content = re.sub(r"```html\n?", "", content)
        content = re.sub(r"```\n?", "", content)
        return content.strip()

    def _extract_title(self, html_content: str) -> Optional[str]:
        """HTML에서 h1 태그 제목 추출"""
        match = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE | re.DOTALL)
        if match:
            # HTML 태그 제거
            title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return title
        return None

    async def generate_title_variations(self, keyword: str, count: int = 5) -> list[str]:
        """키워드에 대한 제목 변형 생성"""
        prompt = f"""다음 키워드에 대해 SEO 최적화된 블로그 제목을 {count}개 생성해주세요.
키워드: {keyword}

요구사항:
- 각 제목은 50-60자
- 키워드를 자연스럽게 포함
- 클릭을 유도하는 매력적인 제목
- 숫자, 의문문, 강조어 등 다양한 형식 사용

제목만 번호와 함께 나열해주세요. 예:
1. 제목1
2. 제목2"""

        response = await gemini_client.generate_content(prompt)
        titles = []
        for line in response.split("\n"):
            line = line.strip()
            if line and re.match(r"^\d+\.", line):
                title = re.sub(r"^\d+\.\s*", "", line).strip()
                if title:
                    titles.append(title)
        return titles[:count]


# 전역 인스턴스
content_generator = ContentGenerator()
