"""
Google Gemini API 클라이언트
AI 콘텐츠 생성을 위한 Gemini API 래퍼
"""
import logging
from typing import Optional
import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API 클라이언트 싱글톤"""

    _instance: Optional["GeminiClient"] = None
    _model = None

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._initialize()

    def _initialize(self):
        """Gemini API 초기화"""
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다. AI 기능을 사용할 수 없습니다.")
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": settings.MAX_CONTENT_TOKENS,
                },
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            )
            logger.info(f"Gemini 모델 '{settings.GEMINI_MODEL}' 초기화 완료")
        except Exception as e:
            logger.error(f"Gemini 초기화 실패: {e}")
            self._model = None

    async def generate_content(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Gemini로 콘텐츠 생성

        Args:
            prompt: 사용자 프롬프트
            system_instruction: 시스템 지시사항 (선택)

        Returns:
            생성된 텍스트
        """
        if not self._model:
            self._initialize()
            if not self._model:
                return self._get_mock_content(prompt)

        try:
            # 시스템 지시사항이 있으면 프롬프트에 포함
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n---\n\n{prompt}"

            response = await self._model.generate_content_async(full_prompt)

            if response and response.text:
                return response.text
            else:
                logger.warning("Gemini 응답이 비어있습니다.")
                return ""

        except Exception as e:
            logger.error(f"Gemini 콘텐츠 생성 실패: {e}")
            raise RuntimeError(f"AI 콘텐츠 생성 중 오류가 발생했습니다: {str(e)}")

    def _get_mock_content(self, prompt: str) -> str:
        """API 키 없을 때 목업 콘텐츠 반환 (개발/테스트용)"""
        return """# 샘플 블로그 포스트

## 소개
이것은 Gemini API 키가 설정되지 않아 생성된 샘플 콘텐츠입니다.
실제 사용 시에는 .env 파일에 GEMINI_API_KEY를 설정해주세요.

## 주요 내용

### 섹션 1
블로그 자동화 시스템 BlogPilot을 사용하면 SEO 최적화된 콘텐츠를 자동으로 생성할 수 있습니다.

### 섹션 2
키워드 리서치부터 워드프레스 자동 발행까지 모든 과정을 자동화합니다.

## 결론
BlogPilot으로 효율적인 블로그 운영을 시작하세요.
"""

    @property
    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부"""
        return self._model is not None


# 전역 싱글톤 인스턴스
gemini_client = GeminiClient()
