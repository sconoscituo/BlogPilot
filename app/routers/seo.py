"""
SEO 최적화 분석 라우터
"""
import json
import re
import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/seo", tags=["SEO 분석"])

try:
    from app.config import config
    GEMINI_KEY = config.GEMINI_API_KEY
except Exception:
    GEMINI_KEY = ""


class SEOAnalysisRequest(BaseModel):
    title: str
    content: str
    target_keyword: Optional[str] = None


class SEOResponse(BaseModel):
    seo_score: int
    title_feedback: str
    keyword_density: float
    readability_score: str  # 상/중/하
    suggestions: List[str]
    meta_description: str
    suggested_tags: List[str]


@router.post("/analyze", response_model=SEOResponse)
async def analyze_seo(
    request: SEOAnalysisRequest,
    current_user: User = Depends(get_current_user),
):
    """블로그 포스트 SEO 분석"""
    if not GEMINI_KEY:
        raise HTTPException(500, "AI 서비스 설정이 필요합니다")

    # 키워드 밀도 계산
    word_count = len(request.content.split())
    keyword_count = request.content.lower().count(request.target_keyword.lower()) if request.target_keyword else 0
    keyword_density = round(keyword_count / word_count * 100, 2) if word_count > 0 else 0.0

    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""다음 블로그 포스트를 SEO 관점에서 분석해줘.

제목: {request.title}
타겟 키워드: {request.target_keyword or '없음'}
내용 (앞 500자): {request.content[:500]}
단어 수: {word_count}

JSON으로 반환 (마크다운 없이):
{{
  "seo_score": 72,
  "title_feedback": "제목에 대한 피드백",
  "readability_score": "중",
  "suggestions": ["개선사항1", "개선사항2", "개선사항3"],
  "meta_description": "검색 결과에 표시될 설명 (160자 이내)",
  "suggested_tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text[text.find("{"):text.rfind("}") + 1]
        data = json.loads(text)
        data["keyword_density"] = keyword_density
        return SEOResponse(**data)
    except Exception:
        raise HTTPException(500, "SEO 분석 중 오류가 발생했습니다")


@router.post("/generate-outline")
async def generate_blog_outline(
    topic: str,
    target_keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """AI 블로그 포스트 목차 생성"""
    if not GEMINI_KEY:
        raise HTTPException(500, "AI 서비스 설정이 필요합니다")

    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        f"주제: {topic}\n타겟 키워드: {target_keyword or topic}\n\n"
        "SEO에 최적화된 블로그 포스트 목차를 H2, H3 구조로 만들어줘. "
        "소개, 본문 4-6섹션, 결론 포함. 마크다운 형식으로."
    )
    return {"topic": topic, "outline": response.text}
