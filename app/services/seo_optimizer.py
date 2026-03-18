"""
SEO 최적화 서비스
생성된 콘텐츠의 SEO 점수를 분석하고 최적화 제안을 제공합니다.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SEOOptimizer:
    """SEO 분석 및 최적화 서비스"""

    def analyze_content(
        self,
        content: str,
        title: str,
        primary_keyword: str,
        meta_description: Optional[str] = None,
    ) -> dict:
        """
        콘텐츠 SEO 종합 분석

        Returns:
            SEO 분석 결과 딕셔너리
        """
        # 순수 텍스트 추출 (HTML 태그 제거)
        plain_text = self._strip_html(content)
        word_count = len(plain_text.split())

        results = {
            "seo_score": 0,
            "word_count": word_count,
            "keyword_density": 0.0,
            "readability_score": 0,
            "issues": [],
            "suggestions": [],
            "checks": {},
        }

        score = 0
        checks = {}

        # 1. 제목 분석 (20점)
        title_score, title_checks = self._analyze_title(title, primary_keyword)
        score += title_score
        checks.update(title_checks)

        # 2. 메타 설명 분석 (10점)
        meta_score, meta_checks = self._analyze_meta_description(meta_description, primary_keyword)
        score += meta_score
        checks.update(meta_checks)

        # 3. 키워드 밀도 분석 (20점)
        kd_score, kd_value, kd_checks = self._analyze_keyword_density(plain_text, primary_keyword)
        score += kd_score
        results["keyword_density"] = kd_value
        checks.update(kd_checks)

        # 4. 콘텐츠 길이 분석 (15점)
        length_score, length_checks = self._analyze_content_length(word_count)
        score += length_score
        checks.update(length_checks)

        # 5. 헤딩 구조 분석 (15점)
        heading_score, heading_checks = self._analyze_headings(content, primary_keyword)
        score += heading_score
        checks.update(heading_checks)

        # 6. 가독성 분석 (10점)
        readability_score, read_value = self._analyze_readability(plain_text)
        score += readability_score
        results["readability_score"] = read_value
        checks["가독성"] = read_value >= 60

        # 7. 링크 분석 (10점)
        link_score, link_checks = self._analyze_links(content)
        score += link_score
        checks.update(link_checks)

        results["seo_score"] = min(100, score)
        results["checks"] = checks
        results["issues"] = self._generate_issues(checks)
        results["suggestions"] = self._generate_suggestions(checks, word_count, results["keyword_density"])

        return results

    def _strip_html(self, html: str) -> str:
        """HTML 태그 제거 후 순수 텍스트 반환"""
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _analyze_title(self, title: str, keyword: str) -> tuple[int, dict]:
        """제목 SEO 분석"""
        checks = {}
        score = 0

        if not title:
            checks["제목 존재"] = False
            return 0, checks

        # 제목에 키워드 포함 (10점)
        keyword_in_title = keyword.lower() in title.lower()
        checks["제목에 키워드 포함"] = keyword_in_title
        if keyword_in_title:
            score += 10

        # 제목 길이 (10점): 30-60자 권장
        title_len = len(title)
        if 30 <= title_len <= 60:
            checks["제목 길이 적절"] = True
            score += 10
        elif 20 <= title_len <= 70:
            checks["제목 길이 적절"] = True
            score += 5
        else:
            checks["제목 길이 적절"] = False

        # 제목 앞부분에 키워드 (추가 점수)
        if keyword_in_title:
            keyword_pos = title.lower().find(keyword.lower())
            if keyword_pos <= len(title) * 0.3:
                checks["제목 앞부분에 키워드"] = True

        return score, checks

    def _analyze_meta_description(self, meta: Optional[str], keyword: str) -> tuple[int, dict]:
        """메타 설명 분석"""
        checks = {}
        score = 0

        if not meta:
            checks["메타 설명 존재"] = False
            return 0, checks

        checks["메타 설명 존재"] = True
        score += 5

        # 길이 체크 (120-160자 권장)
        meta_len = len(meta)
        if 100 <= meta_len <= 160:
            checks["메타 설명 길이 적절"] = True
            score += 3
        else:
            checks["메타 설명 길이 적절"] = False

        # 키워드 포함
        if keyword.lower() in meta.lower():
            checks["메타 설명에 키워드"] = True
            score += 2
        else:
            checks["메타 설명에 키워드"] = False

        return score, checks

    def _analyze_keyword_density(self, text: str, keyword: str) -> tuple[int, float, dict]:
        """키워드 밀도 분석 (권장: 1-2%)"""
        checks = {}
        if not text or not keyword:
            return 0, 0.0, checks

        words = text.lower().split()
        total_words = len(words)
        if total_words == 0:
            return 0, 0.0, checks

        keyword_lower = keyword.lower()
        keyword_count = text.lower().count(keyword_lower)
        density = (keyword_count / total_words) * 100

        score = 0
        if 1.0 <= density <= 2.5:
            score = 20
            checks["키워드 밀도 적절 (1-2.5%)"] = True
        elif 0.5 <= density < 1.0 or 2.5 < density <= 3.5:
            score = 12
            checks["키워드 밀도 적절 (1-2.5%)"] = False
        else:
            score = 0
            checks["키워드 밀도 적절 (1-2.5%)"] = False

        return score, round(density, 2), checks

    def _analyze_content_length(self, word_count: int) -> tuple[int, dict]:
        """콘텐츠 길이 분석"""
        checks = {}
        if word_count >= 2000:
            checks["콘텐츠 길이 충분 (2000+자)"] = True
            return 15, checks
        elif word_count >= 1500:
            checks["콘텐츠 길이 충분 (2000+자)"] = True
            return 12, checks
        elif word_count >= 1000:
            checks["콘텐츠 길이 충분 (2000+자)"] = False
            return 7, checks
        else:
            checks["콘텐츠 길이 충분 (2000+자)"] = False
            return 3, checks

    def _analyze_headings(self, content: str, keyword: str) -> tuple[int, dict]:
        """헤딩 구조 분석"""
        checks = {}
        score = 0

        h2_tags = re.findall(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE | re.DOTALL)
        h3_tags = re.findall(r"<h3[^>]*>(.*?)</h3>", content, re.IGNORECASE | re.DOTALL)

        # H2 존재 여부 (8점)
        if len(h2_tags) >= 3:
            checks["H2 헤딩 3개 이상"] = True
            score += 8
        elif len(h2_tags) >= 1:
            checks["H2 헤딩 3개 이상"] = False
            score += 4
        else:
            checks["H2 헤딩 3개 이상"] = False

        # H3 존재 여부 (4점)
        if len(h3_tags) >= 2:
            checks["H3 헤딩 존재"] = True
            score += 4
        else:
            checks["H3 헤딩 존재"] = False

        # 헤딩에 키워드 포함 (3점)
        all_headings = " ".join(h2_tags + h3_tags).lower()
        if keyword.lower() in all_headings:
            checks["헤딩에 키워드 포함"] = True
            score += 3
        else:
            checks["헤딩에 키워드 포함"] = False

        return score, checks

    def _analyze_readability(self, text: str) -> tuple[int, int]:
        """가독성 분석 (Flesch 유사 점수)"""
        sentences = re.split(r"[.!?。]\s+", text)
        sentence_count = max(1, len(sentences))
        words = text.split()
        word_count = max(1, len(words))

        # 평균 문장 길이
        avg_sentence_length = word_count / sentence_count

        # 가독성 점수 (문장이 짧을수록 높음)
        if avg_sentence_length <= 15:
            readability = 85
        elif avg_sentence_length <= 20:
            readability = 70
        elif avg_sentence_length <= 25:
            readability = 55
        else:
            readability = 40

        score = 10 if readability >= 60 else 5
        return score, readability

    def _analyze_links(self, content: str) -> tuple[int, dict]:
        """링크 분석"""
        checks = {}
        score = 0

        # 내부 링크 확인 (플레이스홀더 포함)
        internal_links = re.findall(r'<a[^>]+href=["\'][^"\']*["\'][^>]*>', content, re.IGNORECASE)
        if len(internal_links) >= 2:
            checks["내부 링크 2개 이상"] = True
            score += 5
        else:
            checks["내부 링크 2개 이상"] = False

        # 외부 링크 확인
        external_links = re.findall(r'href=["\']https?://', content, re.IGNORECASE)
        if len(external_links) >= 1:
            checks["외부 링크 존재"] = True
            score += 5
        else:
            checks["외부 링크 존재"] = False

        return score, checks

    def _generate_issues(self, checks: dict) -> list[str]:
        """실패한 체크 항목 기반 이슈 목록 생성"""
        issues = []
        for check, passed in checks.items():
            if not passed:
                issues.append(f"개선 필요: {check}")
        return issues

    def _generate_suggestions(self, checks: dict, word_count: int, keyword_density: float) -> list[str]:
        """SEO 개선 제안 생성"""
        suggestions = []

        if not checks.get("제목에 키워드 포함"):
            suggestions.append("제목에 주요 키워드를 포함하세요.")

        if not checks.get("메타 설명 존재"):
            suggestions.append("SEO 메타 설명을 120-160자로 작성하세요.")

        if word_count < 2000:
            suggestions.append(f"현재 글자 수({word_count})가 부족합니다. 2000자 이상 권장합니다.")

        if keyword_density < 1.0:
            suggestions.append("키워드 밀도가 낮습니다. 키워드를 더 자주 사용하세요 (권장: 1-2.5%).")
        elif keyword_density > 3.5:
            suggestions.append("키워드 밀도가 높습니다. 키워드 과다 사용은 패널티를 받을 수 있습니다.")

        if not checks.get("H2 헤딩 3개 이상"):
            suggestions.append("H2 헤딩을 3개 이상 사용하여 구조화된 콘텐츠를 만드세요.")

        if not checks.get("내부 링크 2개 이상"):
            suggestions.append("관련 포스트로의 내부 링크를 2개 이상 추가하세요.")

        return suggestions

    def generate_slug(self, keyword: str) -> str:
        """키워드를 URL 슬러그로 변환"""
        # 한글은 그대로 유지하되 공백을 하이픈으로
        slug = keyword.lower().strip()
        slug = re.sub(r"[^\w\s가-힣-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        return slug


# 전역 인스턴스
seo_optimizer = SEOOptimizer()
