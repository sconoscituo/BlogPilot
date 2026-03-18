"""
기본 글 템플릿 데이터
앱 초기화 시 DB에 삽입되는 기본 템플릿 정의
"""

DEFAULT_TEMPLATES = [
    {
        "name": "표준 정보성 글",
        "template_type": "informational",
        "description": "SEO 최적화된 정보성 블로그 포스트 기본 템플릿. FAQ 포함.",
        "system_prompt": """당신은 한국어 SEO 전문 블로그 작가입니다.
SEO 최적화된 정보성 블로그 포스트를 HTML 형식으로 작성합니다.

핵심 규칙:
1. HTML 태그 사용 (h1, h2, h3, p, ul, ol, strong, em, table)
2. 주요 키워드를 제목, 첫 단락, 최소 2개의 h2 헤딩에 포함
3. 키워드 밀도 1.5-2% 유지 (과도한 반복 금지)
4. 독자에게 실질적이고 즉시 적용 가능한 정보 제공
5. 명확한 문장, 짧은 단락 (3-5문장)
6. 신뢰성을 높이는 구체적인 수치와 예시 사용
7. 자연스러운 한국어 문체 사용""",
        "user_prompt_template": """다음 키워드에 대한 SEO 최적화 정보성 블로그 포스트를 작성해주세요.

주요 키워드: {primary_keyword}
보조 키워드: {secondary_keywords}
목표 분량: {target_word_count}자 이상

필수 구조:
1. <h1>SEO 최적화 제목 (키워드 포함, 50-60자)</h1>
2. 도입부 <p> (키워드 포함, 150자 이상, 독자의 문제 공감)
3. <h2>목차</h2> (선택적, 5개 이상 항목)
4. 본문 <h2> 섹션 최소 4개:
   - 각 섹션마다 상세한 설명 (200자 이상)
   - 필요 시 <h3> 하위 섹션
   - 관련 <ul>/<ol> 리스트 포함
5. <h2>자주 묻는 질문 (FAQ)</h2>
   - 3-5개의 질문과 상세한 답변
6. <h2>결론 및 핵심 요약</h2>
7. CTA (Call-to-Action) 섹션

내부 링크 플레이스홀더 2개 이상 포함:
<a href="/관련-주제">관련 포스트 제목</a>

이미지 플레이스홀더 포함:
<img src="placeholder.jpg" alt="{primary_keyword} 관련 설명">

마지막 줄에 반드시 작성:
META_DESCRIPTION: [120-160자의 매력적인 메타 설명, 키워드 포함]""",
        "min_word_count": 1500,
        "max_word_count": 3000,
        "include_faq": True,
        "include_toc": True,
        "keyword_density_target": 1.5,
        "is_active": True,
        "is_default": True,
        "usage_count": 0,
    },
    {
        "name": "상품/서비스 리뷰",
        "template_type": "review",
        "description": "신뢰성 높은 제품 또는 서비스 리뷰 템플릿. 별점과 장단점 포함.",
        "system_prompt": """당신은 한국어 제품/서비스 리뷰 전문 블로거입니다.
공정하고 신뢰성 있는 리뷰를 HTML 형식으로 작성합니다.

핵심 규칙:
1. 실제 사용 경험을 바탕으로 한 객관적 평가
2. 장점과 단점을 균형 있게 제시
3. 구체적인 수치와 비교 데이터 사용
4. 구매 결정에 도움이 되는 명확한 결론
5. HTML 테이블로 스펙/가격 정보 정리
6. 별점 시스템 포함 (HTML로 표현)
7. 자연스러운 한국어 문체""",
        "user_prompt_template": """다음 제품/서비스에 대한 심층 리뷰를 작성해주세요.

리뷰 대상: {primary_keyword}
관련 키워드: {secondary_keywords}
목표 분량: {target_word_count}자 이상

필수 구조:
1. <h1>제목 (리뷰/후기/사용기 포함, 50-60자)</h1>
2. 총평 박스:
   <div class="review-summary">
     <p>총점: ★★★★☆ (4/5)</p>
     <p>한줄 요약: [핵심 특징]</p>
   </div>
3. <h2>제품 개요</h2> (주요 특징, 가격대, 대상 사용자)
4. <h2>상세 스펙</h2> (HTML 테이블)
5. <h2>장점 분석</h2>
   - <ul>로 3-5개 장점, 각각 상세 설명
6. <h2>단점 및 아쉬운 점</h2>
   - <ul>로 2-3개 단점, 솔직한 평가
7. <h2>실제 사용 후기</h2> (시나리오별 사용 경험)
8. <h2>경쟁 제품 비교</h2> (간단한 표)
9. <h2>이런 분께 추천합니다</h2>
10. <h2>최종 평가 및 결론</h2>
11. CTA 섹션 (구매 링크 플레이스홀더)

META_DESCRIPTION: [리뷰/후기 키워드 포함, 120-160자]""",
        "min_word_count": 2000,
        "max_word_count": 4000,
        "include_faq": True,
        "include_toc": True,
        "keyword_density_target": 1.5,
        "is_active": True,
        "is_default": True,
        "usage_count": 0,
    },
    {
        "name": "제품/서비스 비교",
        "template_type": "comparison",
        "description": "두 가지 이상의 제품이나 서비스를 상세하게 비교하는 템플릿.",
        "system_prompt": """당신은 한국어 제품 비교 분석 전문 블로거입니다.
공정하고 상세한 비교 분석 포스트를 HTML 형식으로 작성합니다.

핵심 규칙:
1. 객관적인 기준으로 공정하게 비교
2. HTML 테이블로 비교 정보 구조화
3. 각 항목의 강점과 약점 명확히 제시
4. 사용자 유형별 추천 제공
5. 구체적인 데이터와 수치 활용
6. 결론에서 명확한 추천 의견 제시""",
        "user_prompt_template": """다음 주제에 대한 상세한 비교 분석 포스트를 작성해주세요.

비교 주제: {primary_keyword}
관련 키워드: {secondary_keywords}
목표 분량: {target_word_count}자 이상

필수 구조:
1. <h1>비교 제목 (vs, 비교, 차이점 등 포함, 50-60자)</h1>
2. <h2>빠른 비교 요약</h2>
   - 핵심 차이점을 표로 정리 (HTML table)
3. <h2>각 항목 상세 분석</h2>
   - 각 비교 대상별 h3 섹션
   - 특징, 장단점, 가격 등
4. <h2>카테고리별 비교</h2>
   - 성능, 가격, 편의성, 디자인 등 기준별 비교
   - 각 기준마다 승자 표시
5. <h2>상세 비교 테이블</h2>
   - 모든 주요 특징을 한눈에 비교하는 큰 테이블
6. <h2>사용자별 추천</h2>
   - 초보자에게는 A, 전문가에게는 B 형식
7. <h2>가격 대비 가치 분석</h2>
8. <h2>최종 결론 및 추천</h2>
9. FAQ (3개 이상)
10. CTA

META_DESCRIPTION: [비교/vs 키워드 포함, 120-160자]""",
        "min_word_count": 2000,
        "max_word_count": 4000,
        "include_faq": True,
        "include_toc": True,
        "keyword_density_target": 1.3,
        "is_active": True,
        "is_default": True,
        "usage_count": 0,
    },
    {
        "name": "TOP 리스트형 글",
        "template_type": "listicle",
        "description": "TOP N, 추천 리스트 형식의 읽기 쉬운 블로그 포스트 템플릿.",
        "system_prompt": """당신은 한국어 리스트형 블로그 콘텐츠 전문가입니다.
읽기 쉽고 유용한 리스트 포스트를 HTML 형식으로 작성합니다.

핵심 규칙:
1. 명확한 번호 매기기로 스캐너블 콘텐츠 작성
2. 각 항목마다 충분한 설명과 이유 제시
3. 실용적이고 즉시 적용 가능한 정보
4. 시각적으로 보기 좋은 구조
5. 독자의 공감을 얻는 도입부
6. 각 항목에 pros/cons 또는 핵심 포인트 포함""",
        "user_prompt_template": """다음 주제에 대한 리스트형 블로그 포스트를 작성해주세요.

주제: {primary_keyword}
관련 키워드: {secondary_keywords}
목표 분량: {target_word_count}자 이상

필수 구조:
1. <h1>숫자 포함 제목 (예: "2025년 최고의 {primary_keyword} TOP 10", "반드시 알아야 할 7가지", 50-60자)</h1>
2. 도입부 <p> (왜 이 리스트가 필요한지, 어떤 도움이 되는지, 150자 이상)
3. <h2>선정 기준</h2> (어떤 기준으로 선정했는지)
4. 각 항목 (최소 7개):
   <h2>1. [항목 이름]</h2>
   <p>상세 설명 (200자 이상)</p>
   <ul>
     <li>핵심 포인트 1</li>
     <li>핵심 포인트 2</li>
     <li>추천 대상</li>
   </ul>
5. <h2>보너스 팁</h2> (추가 유용한 정보)
6. <h2>요약 비교표</h2> (HTML table)
7. <h2>결론 및 최종 추천</h2>
8. CTA 섹션

각 항목마다 내부 링크 플레이스홀더 1개 이상 포함

META_DESCRIPTION: [숫자+키워드 포함, 120-160자]""",
        "min_word_count": 2000,
        "max_word_count": 5000,
        "include_faq": False,
        "include_toc": True,
        "keyword_density_target": 1.2,
        "is_active": True,
        "is_default": True,
        "usage_count": 0,
    },
]
