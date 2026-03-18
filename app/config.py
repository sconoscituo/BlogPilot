"""
BlogPilot 설정 관리 모듈
환경 변수를 읽어 애플리케이션 설정을 제공합니다.
"""
import os
import secrets
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """애플리케이션 전역 설정"""

    # 앱 기본 설정
    APP_NAME: str = "BlogPilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("APP_SECRET_KEY", secrets.token_urlsafe(32))

    # 데이터베이스 설정
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./blogpilot.db")

    # Gemini API 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # WordPress 설정
    WORDPRESS_URL: str = os.getenv("WORDPRESS_URL", "")
    WORDPRESS_USERNAME: str = os.getenv("WORDPRESS_USERNAME", "")
    WORDPRESS_APP_PASSWORD: str = os.getenv("WORDPRESS_APP_PASSWORD", "")

    # 스케줄러 설정
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "Asia/Seoul")

    # 이미지 생성 설정
    GENERATED_IMAGES_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_images")

    # 키워드 리서치 설정
    KEYWORD_REQUEST_TIMEOUT: int = 10  # 초
    MAX_KEYWORDS_PER_SEARCH: int = 20

    # 콘텐츠 생성 설정
    MAX_CONTENT_TOKENS: int = 8192
    DEFAULT_LANGUAGE: str = "ko"  # 한국어

    # 구글 서치 콘솔 설정
    GOOGLE_SEARCH_CONSOLE_CREDENTIALS: str = os.getenv("GOOGLE_SEARCH_CONSOLE_CREDENTIALS", "")
    SEARCH_CONSOLE_SITE_URL: str = os.getenv("SEARCH_CONSOLE_SITE_URL", "")

    # 구글 애드센스 설정
    ADSENSE_ACCOUNT_ID: str = os.getenv("ADSENSE_ACCOUNT_ID", "")

    # Unsplash 이미지 설정
    UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")

    @property
    def wordpress_api_url(self) -> str:
        """WordPress REST API 기본 URL"""
        base = self.WORDPRESS_URL.rstrip("/")
        return f"{base}/wp-json/wp/v2"

    @property
    def is_wordpress_configured(self) -> bool:
        """WordPress 설정 완료 여부 확인"""
        return bool(self.WORDPRESS_URL and self.WORDPRESS_USERNAME and self.WORDPRESS_APP_PASSWORD)

    @property
    def is_gemini_configured(self) -> bool:
        """Gemini API 설정 완료 여부 확인"""
        return bool(self.GEMINI_API_KEY)


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환 (캐시됨)"""
    return Settings()


settings = get_settings()
